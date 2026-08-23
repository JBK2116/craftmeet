<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { MeetingSnapshot, Mood } from '$lib/types/meeting';
    import { TriangleAlert, Lightbulb, RefreshCw, Sparkles } from '@lucide/svelte';

    let {
        snapshot = null,
        loading = false,
        ongenerate,
    }: {
        snapshot: MeetingSnapshot | null;
        loading: boolean;
        ongenerate: () => void;
    } = $props();

    const MOOD_STYLES: Record<Mood, string> = {
        positive: 'bg-green-500/10 text-green-600',
        neutral: 'bg-muted text-muted-foreground',
        negative: 'bg-red-500/10 text-red-600',
        mixed: 'bg-amber-500/10 text-amber-600',
        disengaged: 'bg-slate-400/10 text-slate-500',
    };

    let createdAtDisplay = $derived(
        snapshot
            ? new Date(snapshot.created_at).toLocaleTimeString('en-US', {
                  hour: 'numeric',
                  minute: '2-digit',
              })
            : null,
    );
</script>

<div class="rounded-2xl border border-border bg-card p-4 shadow-card">
    <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
            <Sparkles class="h-4 w-4 text-primary" />
            <h3 class="text-sm font-semibold text-(--text-heading)">Snapshot</h3>
        </div>
        <Button size="sm" variant="outline" onclick={ongenerate} disabled={loading}>
            <RefreshCw class="h-4 w-4" />
            {snapshot ? 'Refresh' : 'Generate'}
        </Button>
    </div>

    {#if loading}
        <div class="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw class="h-4 w-4 animate-spin" />
            Generating snapshot…
        </div>
    {:else if snapshot}
        <div class="mt-4 space-y-3">
            <div class="flex items-center justify-between gap-2">
                <span class="text-xs uppercase tracking-wide text-muted-foreground">Mood</span>
                <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium capitalize {MOOD_STYLES[snapshot.mood]}"
                >
                    {snapshot.mood}
                </span>
            </div>

            <div>
                <div
                    class="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground"
                >
                    <TriangleAlert class="h-3.5 w-3.5" />
                    <span>Needs attention</span>
                </div>
                <p class="mt-1 text-sm text-foreground">{snapshot.attention_flag}</p>
            </div>

            <div>
                <div
                    class="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground"
                >
                    <Lightbulb class="h-3.5 w-3.5" />
                    <span>Suggested question</span>
                </div>
                <p class="mt-1 text-sm text-foreground">{snapshot.suggested_question_prompt}</p>
            </div>

            {#if createdAtDisplay}
                <p class="text-xs text-muted-foreground">Generated at {createdAtDisplay}</p>
            {/if}
        </div>
    {:else}
        <p class="mt-4 text-sm text-muted-foreground">
            No snapshot yet. Generate one to get an AI overview of the meeting.
        </p>
    {/if}
</div>
