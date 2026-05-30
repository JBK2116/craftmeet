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
            value: stats.meetings_used_this_month,
            subtext: 'Free plan · unlimited during launch',
        },
        {
            icon: Video,
            label: 'Total Meetings Run',
            value: stats.total_meetings_run,
            subtext: null,
        },
        {
            icon: Users,
            label: 'Total Participants',
            value: stats.total_participants,
            subtext: null,
        },
    ]);
</script>

<!-- cards displayed on page -->
<div class="grid grid-cols-3 gap-3 sm:gap-4">
    {#each cards as card}
        {@const Icon = card.icon}
        <div
            class="shadow-card flex flex-col gap-2 rounded-lg border border-border bg-card p-3 sm:p-4"
        >
            <div class="flex items-center gap-2 text-muted-foreground">
                <Icon class="h-4 w-4 shrink-0" />
                <span class="truncate font-medium" style="font-size: var(--text-label)">
                    {card.label}
                </span>
            </div>
            <span class="font-semibold text-foreground" style="font-size: var(--text-heading)">
                {card.value}
            </span>
            {#if card.subtext}
                <span class="text-meta hidden sm:block">{card.subtext}</span>
            {/if}
        </div>
    {/each}
</div>
