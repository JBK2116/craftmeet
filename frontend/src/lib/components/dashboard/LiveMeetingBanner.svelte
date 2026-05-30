<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { Meeting } from '$lib/types/meeting';
    import { timeAgo } from '$lib/utils/time';
    import { ArrowRight, Users } from '@lucide/svelte';

    // current live meeting
    const { meeting }: { meeting: Meeting } = $props();
</script>

<section
    class="shadow-card flex flex-col gap-4 rounded-lg border border-border border-l-4 border-l-primary bg-primary/5 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
    aria-label="Live meeting"
>
    <!-- Header -->
    <div class="flex min-w-0 flex-col gap-2">
        <div class="flex items-center gap-2">
            <span class="relative flex h-2.5 w-2.5">
                <span
                    class="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"
                ></span>
                <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary"></span>
            </span>
            <span
                class="font-semibold tracking-wide text-primary uppercase"
                style="font-size: var(--text-label)"
            >
                Live now
            </span>
        </div>
        <!-- Meeting Title -->
        <h3 class="truncate text-foreground">{meeting.title}</h3>
        <!-- Meeting Details -->
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span class="text-room-code">{meeting.room_code}</span>
            <span class="flex items-center gap-1.5 text-meta">
                <Users class="h-4 w-4" />
                {meeting.participant_count ?? 0} participants
            </span>
            {#if meeting.started_at}
                <span class="text-meta">Started {timeAgo(meeting.started_at)}</span>
            {/if}
        </div>
    </div>
    <!-- Action Buttons -->
    <Button href={`/meetings/${meeting.id}/host`} class="shrink-0 sm:self-center">
        Rejoin Session
        <ArrowRight class="h-4 w-4" />
    </Button>
</section>
