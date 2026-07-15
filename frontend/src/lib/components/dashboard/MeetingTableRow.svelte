<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { MeetingIn } from '$lib/types/meeting';
    import { timeAgo } from '$lib/utils/time';

    // current selected meeting in the table
    const { meeting }: { meeting: MeetingIn } = $props();
</script>

<tr class="border-b border-border transition-colors last:border-0 hover:bg-muted/40">
    <!-- Title + Status -->
    <td class="px-3 py-2.5 align-middle">
        <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-foreground">{meeting.title}</span>
            <div class="flex items-center gap-2">
                {#if meeting.status === 'draft'}
                    <span class="mt-0.5 text-xs text-muted-foreground">Continue building →</span>
                {:else if meeting.status === 'live'}
                    <span class="mt-0.5 text-xs text-muted-foreground">Session active →</span>
                {:else}
                    <span class="mt-0.5 text-xs text-muted-foreground">Review responses →</span>
                {/if}
            </div>
        </div>
    </td>

    <!-- Question Count -->
    <td class="hidden px-3 py-2.5 align-middle text-xs text-muted-foreground md:table-cell">
        {meeting.total_questions} questions
    </td>


    <!-- Created At -->
    <td class="hidden px-3 py-2.5 align-middle text-xs text-muted-foreground md:table-cell">
        {timeAgo(meeting.created_at)}
    </td>

    <!-- Actions -->
    <td class="px-3 py-2.5 text-right align-middle">
        <Button
            href={`/meetings/${meeting.id}`}
            variant="ghost"
            size="sm"
            class="text-xs font-medium hover:bg-accent hover:text-primary dark:hover:bg-accent"
            >View</Button
        >
    </td>
</tr>
