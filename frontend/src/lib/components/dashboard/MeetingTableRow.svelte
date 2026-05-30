<script lang="ts">
    import { Badge } from '$lib/components/ui/badge';
    import { Button } from '$lib/components/ui/button';
    import type { Meeting } from '$lib/types/meeting';
    import { timeAgo } from '$lib/utils/time';

    // current selected meeting in the table
    const { meeting }: { meeting: Meeting } = $props();

    // dynamic color depending on meeting status
    const statusClass = $derived(
        {
            live: 'bg-green-500/10 text-green-600 border-green-500/20',
            draft: 'bg-muted text-muted-foreground',
            completed: 'bg-secondary text-secondary-foreground',
        }[meeting.status],
    );
</script>

<tr class="border-b border-border transition-colors hover:bg-muted/40">
    <!-- Title + Status -->
    <td class="py-3 pr-3 align-middle">
        <div class="flex flex-col gap-1">
            <span class="font-medium text-foreground">{meeting.title}</span>
            <div class="flex items-center gap-2">
                <Badge class={statusClass}>{meeting.status}</Badge>
                {#if meeting.status === 'draft'}
                    <span class="text-meta">Continue building →</span>
                {/if}
            </div>
        </div>
    </td>

    <!-- Question Count -->
    <td class="hidden px-3 py-3 align-middle text-muted-foreground md:table-cell">
        {meeting.question_count} questions
    </td>

    <!-- Participant Count -->
    <td class="hidden px-3 py-3 align-middle text-muted-foreground md:table-cell">
        {#if meeting.status === 'completed'}
            {meeting.participant_count ?? 0} joined
        {:else if meeting.status === 'live'}
            <span class="inline-flex items-center gap-1.5">
                <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500"></span>
                {meeting.participant_count ?? 0} live
            </span>
        {:else}
            --
        {/if}
    </td>

    <!-- Created At -->
    <td class="hidden px-3 py-3 align-middle text-muted-foreground md:table-cell">
        {timeAgo(meeting.created_at)}
    </td>

    <!-- Actions -->
    <td class="py-3 pl-3 text-right align-middle">
        <Button href={`/meetings/${meeting.id}`} variant="ghost" size="sm">View</Button>
    </td>
</tr>
