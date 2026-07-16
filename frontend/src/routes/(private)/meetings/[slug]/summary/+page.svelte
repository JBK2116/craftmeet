<script lang="ts">
    import { goto } from '$app/navigation';
    import { apiFetch } from '$lib/api/auth';
    import { AuthError, RateLimitedError } from '$lib/types/errors';
    import type { MeetingIn, Stat } from '$lib/types/meeting';
    import type { QuestionTypes } from '$lib/types/question';
    import { formatDuration } from '$lib/utils/time';
    import {
        AlignStartVertical,
        ArrowLeft,
        ChartBar,
        CheckCheck,
        Clock,
        FileText,
        Hash,
        ListChecks,
        MessageSquareText,
        Sparkles,
        Star,
        ToggleLeft,
        Trash2,
        Users,
    } from '@lucide/svelte';
    import { untrack } from 'svelte';
    import { toast } from 'svelte-sonner';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    // meeting data
    let meeting: MeetingIn = $state(untrack(() => data.meeting));
    let generating = $state(false);
    let showDeleteConfirm = $state(false);
    let deleting = $state(false);

    // Stat display cards
    type StatCard = { icon: typeof Users; label: string; value: string | number; subtext?: string };

    let statCards = $derived.by((): StatCard[] => {
        const s: Stat | undefined = meeting.stats;
        return [
            { icon: Users, label: 'Participants', value: s?.total_participants ?? '—' },
            { icon: Hash, label: 'Questions Asked', value: s?.total_questions_asked ?? '—' },
            {
                icon: MessageSquareText,
                label: 'Responses',
                value: s?.total_responses_received ?? '—',
            },
            {
                icon: ChartBar,
                label: 'Response Rate',
                value: s ? `${Math.round(s.average_response_rate * 100)}%` : '—',
            },
            {
                icon: Clock,
                label: 'Duration',
                value:
                    meeting.started_at && meeting.ended_at
                        ? formatDuration(meeting.started_at, meeting.ended_at)
                        : '—',
            },
        ];
    });

    // Question type icons
    const TYPE_ICONS: Record<QuestionTypes, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        yes_no: ToggleLeft,
    };

    const TYPE_LABELS: Record<QuestionTypes, string> = {
        multiple_choice: 'Multiple Choice',
        long_answer: 'Long Answer',
        ranked_voting: 'Ranked Voting',
        rating_scale: 'Rating Scale',
        yes_no: 'Yes / No',
    };

    // Sort questions by position
    let sortedQuestions = $derived([...meeting.questions].sort((a, b) => a.position - b.position));

    // derived status display
    let statusLabel = $derived(
        meeting.status === 'completed' ? 'Completed' : meeting.status === 'live' ? 'Live' : 'Draft',
    );

    let statusClass = $derived(
        meeting.status === 'completed'
            ? 'bg-muted text-muted-foreground'
            : meeting.status === 'live'
              ? 'bg-primary/10 text-primary'
              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    );

    /**
     * Formats an ISO date string into a human-readable locale date.
     *
     * @param iso - An ISO 8601 date string, or null.
     * @returns A formatted date string like "Jul 13, 2026, 2:30 PM", or "—" if null.
     */
    function formatDate(iso: string | null): string {
        if (!iso) return '—';
        return new Date(iso).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
    }

    /**
     * Requests an AI-generated meeting summary to the backend.
     *
     * Sends a POST request to the summary endpoint. On success the backend
     * returns a file (PDF/text) which is automatically downloaded via a
     * temporary anchor element.
     */
    async function handleGenerateSummary() {
        if (generating) return;
        generating = true;
        try {
            const url = `/api/v1/meetings/${meeting.id}/summary`;
            const opts: RequestInit = {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
            };
            const res = await apiFetch(url, opts);
            if (!res.ok) {
                if (res.status === 501) {
                    toast.info('AI summaries are coming soon!');
                    return;
                }
                throw new Error(`Failed to generate summary: ${res.status}`);
            }
            // Extract filename from Content-Disposition header, fall back to meeting title
            const disposition = res.headers.get('Content-Disposition');
            const filenameMatch = disposition?.match(/filename="?(.+?)"?$/);
            const filename = filenameMatch?.[1] ?? `${meeting.title.replace(/\s+/g, '_')}_summary`;
            const blob = await res.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            toast.success('Summary downloaded!');
        } catch (err: any) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message)
                return
            }
            toast.error('Could not generate summary. Please try again.');
        } finally {
            generating = false;
        }
    }

    /**
     * Deletes the current meeting and redirects to the dashboard.
     *
     * Shows a full-screen loading overlay while the DELETE request is in flight.
     * On success displays a toast with the meeting title and navigates away.
     */
    async function handleDeleteMeeting() {
        deleting = true;
        try {
            const url = `/api/v1/meetings/${meeting.id}`;
            const opts: RequestInit = { method: 'DELETE', credentials: 'include' };
            const res = await apiFetch(url, opts);
            if (!res.ok) {
                throw new Error(`Failed to delete meeting: ${meeting.id}`);
            }
            toast.success(`"${meeting.title}" has been deleted.`);
            goto('/dashboard');
        } catch (err: any) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message)
                return
            }
            toast.error('Failed to delete meeting. Please try again.');
        } finally {
            deleting = false;
        }
    }
</script>

<div class="mx-auto max-w-3xl px-4 py-8 md:px-6">
    <!-- Back navigation -->
    <button
        onclick={() => goto(`/meetings/${meeting.id}`)}
        class="group mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
        <ArrowLeft class="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
        Back to meeting
    </button>

    <!-- Header -->
    <div class="mb-8">
        <div class="mb-3 flex flex-wrap items-center gap-3">
            <h1
                class="text-[var(--text-heading)] font-bold leading-tight tracking-tight break-words"
            >
                {meeting.title}
            </h1>
            <span
                class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {statusClass}"
            >
                {statusLabel}
            </span>
        </div>
        {#if meeting.description}
            <p class="text-meta mb-2">{meeting.description}</p>
        {/if}
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
            <span>Created {formatDate(meeting.created_at)}</span>
            {#if meeting.started_at}
                <span>Started {formatDate(meeting.started_at)}</span>
            {/if}
            {#if meeting.ended_at}
                <span>Ended {formatDate(meeting.ended_at)}</span>
            {/if}
        </div>
    </div>

    <!-- Stats Grid -->
    <section class="mb-8">
        <h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Meeting Stats
        </h2>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {#each statCards as card}
                {@const Icon = card.icon}
                <div
                    class="flex flex-col gap-1 rounded-xl border border-border bg-card px-4 py-3.5"
                >
                    <div class="flex items-center gap-1.5 text-muted-foreground">
                        <Icon class="h-3.5 w-3.5 shrink-0" />
                        <span class="truncate text-xs">{card.label}</span>
                    </div>
                    <span class="text-lg font-semibold text-foreground tabular-nums">
                        {card.value}
                    </span>
                </div>
            {/each}
        </div>
    </section>

    <!-- Generate Summary -->
    <section class="mb-8">
        <div
            class="flex flex-col gap-4 rounded-xl border border-border bg-card p-5 sm:flex-row sm:items-center sm:justify-between"
        >
            <div>
                <h3 class="text-sm font-semibold text-foreground">AI Summary</h3>
                <p class="text-xs text-muted-foreground">
                    Generate an AI-powered summary of this meeting's activity and responses.
                </p>
            </div>
            <button
                onclick={handleGenerateSummary}
                disabled={generating}
                class="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
            >
                {#if generating}
                    <span
                        class="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground"
                    ></span>
                    Generating…
                {:else}
                    <Sparkles class="h-4 w-4" />
                    Generate Summary
                {/if}
            </button>
        </div>
    </section>

    <!-- Questions -->
    <section>
        <h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Questions
            <span
                class="ml-1.5 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
            >
                {meeting.questions.length}
            </span>
        </h2>

        {#if sortedQuestions.length === 0}
            <div
                class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-12 text-center"
            >
                <FileText class="h-8 w-8 text-muted-foreground/50" />
                <p class="text-sm text-muted-foreground">No questions in this meeting.</p>
            </div>
        {:else}
            <div class="space-y-3">
                {#each sortedQuestions as q, i}
                    {@const Icon = TYPE_ICONS[q.type]}
                    {@const statusLabel =
                        q.status === 'open' ? 'Open' : q.status === 'closed' ? 'Closed' : 'Pending'}
                    <div
                        class="flex items-start gap-4 rounded-xl border border-border bg-card px-5 py-4 transition-colors"
                    >
                        <span
                            class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-semibold text-muted-foreground tabular-nums"
                        >
                            {i + 1}
                        </span>
                        <div class="min-w-0 flex-1">
                            <p class="text-sm font-medium text-foreground break-words">
                                {q.prompt}
                            </p>
                            <div class="mt-1.5 flex items-center gap-2">
                                <div
                                    class="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5"
                                >
                                    <Icon class="h-3 w-3 text-primary" />
                                    <span class="text-xs font-medium text-primary">
                                        {TYPE_LABELS[q.type]}
                                    </span>
                                </div>
                                <span
                                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium {q.status ===
                                    'open'
                                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                        : q.status === 'closed'
                                          ? 'bg-muted text-muted-foreground'
                                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}"
                                >
                                    {statusLabel}
                                </span>
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </section>

    <!-- Bottom actions -->
    <div
        class="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6"
    >
        <button
            onclick={() => goto('/dashboard')}
            class="inline-flex items-center justify-center rounded-xl border border-border bg-card px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
        >
            Back to Dashboard
        </button>
        <button
            onclick={() => goto(`/meetings/${meeting.id}`)}
            class="inline-flex items-center justify-center rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
            <CheckCheck class="mr-1.5 h-4 w-4" />
            Meeting Details
        </button>
    </div>

    <!-- Delete button -->
    <div class="mt-6 flex justify-center border-t border-border pt-6">
        <button
            onclick={() => (showDeleteConfirm = true)}
            class="inline-flex items-center justify-center gap-1.5 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20 focus:outline-none focus:ring-2 focus:ring-ring"
        >
            <Trash2 class="h-4 w-4" />
            Delete Meeting
        </button>
    </div>
</div>

{#if deleting}
    <div
        class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm"
    >
        <div class="flex flex-col items-center gap-4">
            <div
                class="h-8 w-8 rounded-full border-2 border-muted border-t-primary animate-spin"
            ></div>
            <p class="text-sm text-muted-foreground">Deleting meeting&hellip;</p>
        </div>
    </div>
{:else if showDeleteConfirm}
    <!-- Delete confirmation overlay -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
        role="dialog"
        aria-modal="true"
    >
        <div
            class="mx-4 w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-overlay"
        >
            <h3 class="mb-2 text-lg font-semibold text-[var(--text-heading)]">Delete Meeting?</h3>
            <p class="mb-6 text-sm text-muted-foreground">
                This will permanently delete &ldquo;{meeting.title}&rdquo; and all associated
                questions, responses, and stats. This action cannot be undone.
            </p>
            <div class="flex gap-3">
                <button
                    onclick={() => (showDeleteConfirm = false)}
                    class="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    Cancel
                </button>
                <button
                    onclick={() => {
                        showDeleteConfirm = false;
                        handleDeleteMeeting();
                    }}
                    class="flex-1 rounded-xl bg-destructive px-4 py-2.5 text-sm font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    Delete
                </button>
            </div>
        </div>
    </div>
{/if}
