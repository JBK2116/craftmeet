<script lang="ts">
    import { goto } from '$app/navigation';
    import { apiFetch } from '$lib/api/auth';
    import { user } from '$lib/stores/stores';
    import { AuthError, ErrorTypes, RateLimitedError } from '$lib/types/errors';
    import type { User } from '$lib/types/user';
    import {
        BadgeCheck,
        Calendar,
        CircleUserRound,
        Crown,
        Globe,
        Mail,
        Pencil,
        Shield,
        Trash2,
        Users,
        Video,
    } from '@lucide/svelte';
    import { untrack } from 'svelte';
    import { toast } from 'svelte-sonner';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    let pageUser = $state(untrack(() => data.user as User));
    let editingUsername = $state(false);
    let usernameInput = $state(untrack(() => pageUser.username ?? ''));

    const joinedDate = $derived(
        new Date(pageUser.created_at).toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric',
        }),
    );

    const lastUpdated = $derived(
        new Date(pageUser.updated_at).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        }),
    );

    const planLabel = $derived.by(() => {
        switch (pageUser.meeting_plan) {
            case 'free':
                return 'Free';
            case 'pro':
                return 'Pro';
            case 'team':
                return 'Team';
            default:
                return 'Free';
        }
    });

    function startEditing() {
        usernameInput = pageUser.username ?? '';
        editingUsername = true;
    }

    function cancelEditing() {
        editingUsername = false;
        usernameInput = pageUser.username ?? '';
    }

    async function saveUsername() {
        const trimmed = usernameInput.trim();
        if (trimmed && trimmed !== pageUser.username) {
            // snapshot for rollback
            const prevUser = pageUser;
            const prevStore = $user;
            // update local store optimistically
            $user = $user ? { ...$user, username: trimmed } : null;
            pageUser = { ...pageUser, username: trimmed };
            try {
                const url = `/api/v1/auth/me`;
                const payload = { username: trimmed };
                const opts: RequestInit = {
                    method: 'PATCH',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                };
                const response = await apiFetch(url, opts);
                const body = await response.json();
                if (!response.ok) {
                    // roll back optimistic update on error
                    $user = prevStore;
                    pageUser = prevUser;
                    switch (body.type) {
                        case ErrorTypes.USERNAME:
                            toast.error(body.message);
                            return;
                        case ErrorTypes.SERVER:
                            toast.error(
                                'We could not update your username, There was a temporary problem with our service. Please try again soon',
                            );
                            return;
                        default:
                            toast.error(
                                'We could not update your username. Please try again later.',
                            );
                            return;
                    }
                }
                const updated_user = body as User;
                user.set(updated_user);
                pageUser = updated_user;
                editingUsername = false;
                toast.success('Your username has been updated successfully.');
                return;
            } catch (err: any) {
                // roll back optimistic update on error
                $user = prevStore;
                pageUser = prevUser;
                if (err instanceof AuthError) {
                    return;
                }
                if (err instanceof RateLimitedError) {
                    toast.error(err.message);
                    return;
                }
                throw err;
            }
        }
        editingUsername = false;
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            saveUsername();
        } else if (e.key === 'Escape') {
            cancelEditing();
        }
    }

    // Sync pageUser when the store changes (e.g. after login redirect)
    $effect(() => {
        if ($user) {
            pageUser = $user;
        }
    });

    // Danger zone
    let showDeleteConfirm = $state(false);

    async function handleDeleteAllMeetings() {
        const url = `/api/v1/meetings`;
        const opts: RequestInit = { method: 'DELETE', credentials: 'include' };
        try {
            const response = await apiFetch(url, opts);
            if (!response.ok) {
                toast.error('Failed to delete all meetings. Please try again.');
                showDeleteConfirm = false;
                return;
            }
            toast.success('All meetings cleared');
            showDeleteConfirm = false;
        } catch (err: any) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message);
                return;
            }
            throw err;
        }
    }
</script>

<div class="mx-auto max-w-5xl space-y-5 px-4 py-6 md:px-6">
    <!-- Page header -->
    <header>
        <h2 class="text-lg font-semibold text-foreground">Account</h2>
        <p class="text-sm text-muted-foreground">Manage your profile, plan, and account details</p>
    </header>

    <!-- Profile card -->
    <section class="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div class="flex items-start gap-5">
            <!-- Avatar -->
            <div
                class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"
            >
                <CircleUserRound class="h-8 w-8" />
            </div>

            <div class="min-w-0 flex-1">
                <!-- Username row with inline edit -->
                <div class="group flex items-center gap-2">
                    {#if editingUsername}
                        <div class="flex items-center gap-2">
                            <!-- svelte-ignore a11y_autofocus -->
                            <input
                                type="text"
                                bind:value={usernameInput}
                                onkeydown={handleKeydown}
                                autofocus
                                maxlength={50}
                                class="h-8 rounded-md border border-input bg-background px-2 text-sm font-semibold text-foreground outline-ring/40 focus:border-primary/50 focus:outline-none"
                            />
                            <button
                                onclick={saveUsername}
                                class="inline-flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-medium text-primary-foreground transition hover:bg-primary/90"
                                aria-label="Save username"
                            >
                                &#10003;
                            </button>
                            <button
                                onclick={cancelEditing}
                                class="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border text-xs text-muted-foreground transition hover:bg-accent"
                                aria-label="Cancel"
                            >
                                &#10005;
                            </button>
                        </div>
                    {:else}
                        <h3 class="truncate text-lg font-semibold text-foreground">
                            {pageUser.username ?? 'Unnamed'}
                        </h3>
                        <button
                            onclick={startEditing}
                            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 transition hover:bg-accent hover:text-accent-foreground group-hover:opacity-100 focus:opacity-100"
                            aria-label="Edit username"
                        >
                            <Pencil class="h-3.5 w-3.5" />
                        </button>
                    {/if}
                </div>

                <!-- Email -->
                <div class="mt-0.5 flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Mail class="h-3.5 w-3.5 shrink-0" />
                    <span class="truncate">{pageUser.email}</span>
                </div>

                <!-- Meta row: verified, joined, google -->
                <div
                    class="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground"
                >
                    {#if pageUser.verified}
                        <span
                            class="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-500"
                        >
                            <BadgeCheck class="h-3.5 w-3.5" />
                            Verified
                        </span>
                    {:else}
                        <span
                            class="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500"
                        >
                            <Shield class="h-3.5 w-3.5" />
                            Not verified
                        </span>
                    {/if}

                    <span class="inline-flex items-center gap-1">
                        <Calendar class="h-3.5 w-3.5" />
                        Joined {joinedDate}
                    </span>

                    {#if pageUser.google_id}
                        <span class="inline-flex items-center gap-1">
                            <Globe class="h-3.5 w-3.5" />
                            Google connected
                        </span>
                    {/if}
                </div>
            </div>
        </div>
    </section>

    <!-- Plan card -->
    <section class="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div class="flex items-start justify-between gap-4">
            <div class="flex items-center gap-3">
                <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10"
                >
                    <Crown class="h-5 w-5 text-primary" />
                </div>
                <div>
                    <p class="text-sm font-medium text-foreground">
                        {planLabel} Plan
                    </p>
                    <p class="text-xs text-muted-foreground">Unlimited meetings during launch</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Meeting Stats -->
    <section class="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div class="grid grid-cols-1 sm:grid-cols-3">
            <!-- Total meetings -->
            <div
                class="flex items-center gap-3 border-b border-border px-5 py-4 last:border-b-0 sm:border-b-0 sm:border-r"
            >
                <div
                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10"
                >
                    <Video class="h-4 w-4 text-primary" />
                </div>
                <div class="min-w-0">
                    <p class="text-sm font-medium text-foreground">
                        {pageUser.total_meetings}
                    </p>
                    <p class="truncate text-xs text-muted-foreground">Total meetings run</p>
                </div>
            </div>

            <!-- Meetings this month -->
            <div
                class="flex items-center gap-3 border-b border-border px-5 py-4 last:border-b-0 sm:border-b-0 sm:border-r"
            >
                <div
                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10"
                >
                    <Calendar class="h-4 w-4 text-primary" />
                </div>
                <div class="min-w-0">
                    <p class="text-sm font-medium text-foreground">
                        {pageUser.total_meetings_month}
                    </p>
                    <p class="truncate text-xs text-muted-foreground">Meetings this month</p>
                </div>
            </div>

            <!-- Total participants -->
            <div class="flex items-center gap-3 px-5 py-4">
                <div
                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10"
                >
                    <Users class="h-4 w-4 text-primary" />
                </div>
                <div class="min-w-0">
                    <p class="text-sm font-medium text-foreground">
                        {pageUser.total_participants}
                    </p>
                    <p class="truncate text-xs text-muted-foreground">Total participants</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Security / Account meta -->
    <section class="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div class="flex items-center gap-2.5">
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <Shield class="h-4 w-4 text-primary" />
            </div>
            <div>
                <p class="text-sm font-medium text-foreground">Security</p>
            </div>
        </div>

        <div class="mt-4 space-y-3">
            <div
                class="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-4 py-2.5"
            >
                <span class="text-sm text-muted-foreground">Email verified</span>
                {#if pageUser.verified}
                    <span
                        class="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-500"
                    >
                        <BadgeCheck class="h-3 w-3" />
                        Yes
                    </span>
                {:else}
                    <span
                        class="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-500"
                    >
                        No
                    </span>
                {/if}
            </div>

            {#if pageUser.google_id}
                <div
                    class="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-4 py-2.5"
                >
                    <span class="text-sm text-muted-foreground">Google account</span>
                    <span
                        class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary"
                    >
                        <Globe class="h-3 w-3" />
                        Connected
                    </span>
                </div>
            {/if}

            <div
                class="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-4 py-2.5"
            >
                <span class="text-sm text-muted-foreground">Last updated</span>
                <span class="text-xs text-foreground">{lastUpdated}</span>
            </div>

            <details class="group">
                <summary
                    class="cursor-pointer list-none rounded-lg border border-border bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground transition hover:bg-muted/60"
                >
                    <span class="inline-flex items-center gap-1.5">
                        Advanced
                        <span
                            class="text-xs text-muted-foreground/60 transition group-open:rotate-180"
                            >&#9660;</span
                        >
                    </span>
                </summary>
                <div class="mt-2 space-y-2 px-4">
                    <div class="flex items-center justify-between py-1">
                        <span class="text-xs text-muted-foreground">User ID</span>
                        <code class="text-xs text-foreground/60">{pageUser.id}</code>
                    </div>
                    <div class="flex items-center justify-between py-1">
                        <span class="text-xs text-muted-foreground">Created</span>
                        <span class="text-xs text-foreground/60">{joinedDate}</span>
                    </div>
                </div>
            </details>
        </div>
    </section>

    <!-- Danger Zone -->
    <section class="rounded-xl border border-destructive/20 bg-card p-6 shadow-sm">
        <div class="flex items-center gap-2.5">
            <div
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10"
            >
                <Trash2 class="h-4 w-4 text-destructive" />
            </div>
            <div>
                <p class="text-sm font-medium text-foreground">Danger Zone</p>
                <p class="text-xs text-muted-foreground">
                    Irreversible actions that affect your account data
                </p>
            </div>
        </div>

        <div
            class="mt-4 flex items-center justify-between rounded-lg border border-destructive/20 bg-muted/40 px-4 py-3"
        >
            <div class="min-w-0">
                <p class="text-sm font-medium text-foreground">Delete all meetings</p>
                <p class="text-xs text-muted-foreground">
                    Permanently remove every meeting you've created
                </p>
            </div>

            {#if showDeleteConfirm}
                <div class="flex shrink-0 items-center gap-2">
                    <button
                        onclick={handleDeleteAllMeetings}
                        class="inline-flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs font-medium text-destructive transition hover:bg-destructive/20 focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        Confirm
                    </button>
                    <button
                        onclick={() => (showDeleteConfirm = false)}
                        class="inline-flex items-center justify-center rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        Cancel
                    </button>
                </div>
            {:else}
                <button
                    onclick={() => (showDeleteConfirm = true)}
                    class="inline-flex shrink-0 items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs font-medium text-destructive transition hover:bg-destructive/20 focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <Trash2 class="mr-1.5 h-3.5 w-3.5" />
                    Delete
                </button>
            {/if}
        </div>
    </section>
</div>
