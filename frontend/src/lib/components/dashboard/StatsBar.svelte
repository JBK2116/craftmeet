<script lang="ts">
    import type { User } from '$lib/types/user';
    import { CalendarCheck, Users, Video } from '@lucide/svelte';

    // user object containing stats
    const { stats }: { stats: User } = $props();

    // stat cards related to meetings
    const cards = $derived([
        {
            icon: CalendarCheck,
            label: 'Meetings This Month',
            value: stats.total_meetings_month,
            subtext: 'Free plan · unlimited during launch',
        },
        { icon: Video, label: 'Total Meetings Run', value: stats.total_meetings, subtext: null },
        {
            icon: Users,
            label: 'Total Participants',
            value: stats.total_participants,
            subtext: null,
        },
    ]);
</script>

<!-- cards displayed on page -->
<div class="grid grid-cols-1 overflow-hidden rounded-lg border border-border sm:grid-cols-3">
    {#each cards as card}
        {@const Icon = card.icon}
        <div
            class="flex flex-col gap-0.5 border-b border-border bg-card px-4 py-3 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0"
        >
            <div class="flex items-center gap-2 text-muted-foreground">
                <Icon class="h-4 w-4 shrink-0" />
                <span class="truncate text-xs">
                    {card.label}
                </span>
            </div>
            <span class="text-lg font-semibold text-foreground">
                {card.value}
            </span>
            {#if card.subtext}
                <span class="text-meta hidden text-xs sm:block">{card.subtext}</span>
            {/if}
        </div>
    {/each}
</div>
