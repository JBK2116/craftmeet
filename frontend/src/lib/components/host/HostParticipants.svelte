<script lang="ts">
    import type { Participant } from '$lib/types/participant';
    import { Users, X } from '@lucide/svelte';

    let {
        open,
        participants,
        onclose,
    }: {
        open: boolean;
        participants: Participant[];
        onclose: () => void;
    } = $props();

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) onclose();
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') onclose();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
        onclick={handleBackdropClick}
        role="dialog"
        aria-modal="true"
        aria-label="Participants"
    >
        <!-- Modal panel -->
        <div class="w-full max-w-sm overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-border px-5 py-4">
                <div class="flex items-center gap-2">
                    <Users class="h-4 w-4 text-muted-foreground" />
                    <h2 class="text-sm font-semibold text-[var(--text-heading)]">
                        Participants ({participants.length})
                    </h2>
                </div>
                <button
                    onclick={onclose}
                    class="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    aria-label="Close"
                >
                    <X class="h-4 w-4" />
                </button>
            </div>

            <!-- Body -->
            <div class="max-h-80 overflow-y-auto px-5 py-4">
                {#if participants.length === 0}
                    <div class="flex flex-col items-center gap-2 py-10 text-center">
                        <Users class="h-8 w-8 text-muted-foreground/40" />
                        <p class="text-sm text-muted-foreground">No participants yet</p>
                        <p class="text-xs text-muted-foreground/60">
                            Share the room code to invite participants
                        </p>
                    </div>
                {:else}
                    <div class="space-y-1">
                        {#each participants as p (p.id)}
                            <div
                                class="flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50"
                            >
                                <div
                                    class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                                >
                                    {p.username.charAt(0).toUpperCase()}
                                </div>
                                <div class="min-w-0 flex-1">
                                    <p class="truncate text-sm font-medium text-foreground">
                                        {p.username}
                                    </p>
                                </div>
                                <span
                                    class="flex items-center gap-1.5 text-xs {p.connected
                                        ? 'text-green-500'
                                        : 'text-muted-foreground'}"
                                >
                                    <span
                                        class="h-2 w-2 rounded-full {p.connected ? 'bg-green-500' : 'bg-muted-foreground/30'}"
                                    ></span>
                                    {p.connected ? 'Online' : 'Offline'}
                                </span>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}
