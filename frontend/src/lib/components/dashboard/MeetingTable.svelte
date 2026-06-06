<script lang="ts">
    import type { Meeting } from '$lib/types/meeting';

    import EmptyState from './EmptyState.svelte';
    import MeetingTableRow from './MeetingTableRow.svelte';

    // user's meetings array
    const { meetings }: { meetings: Meeting[] } = $props();

    // filter based on meeting status type
    type Tab = 'Upcoming' | 'Drafts' | 'Completed';
    const tabs: Tab[] = ['Upcoming', 'Drafts', 'Completed'];
    const tabStatus: Record<Tab, Meeting['status']> = {
        Upcoming: 'live',
        Drafts: 'draft',
        Completed: 'completed',
    };

    // current filter type
    let activeTab = $state<Tab>('Upcoming');

    const filtered = $derived(meetings.filter((m) => m.status === tabStatus[activeTab]));
</script>

<div class="flex flex-col">
    <!-- Filter tabs -->
    <div class="mb-0 flex gap-0 border-b border-border" role="tablist">
        {#each tabs as tab}
            <button
                role="tab"
                aria-selected={activeTab === tab}
                onclick={() => (activeTab = tab)}
                class={activeTab === tab
                    ? '-mb-px border-b-2 border-primary px-3 py-2 text-sm font-medium text-foreground'
                    : 'px-3 py-2 text-sm text-muted-foreground hover:text-foreground'}
            >
                {tab}
            </button>
        {/each}
    </div>

    <!-- Meeting Table -->
    <div class="max-h-[420px] overflow-y-auto scroll-thin">
        {#if filtered.length === 0}
            <EmptyState tab={activeTab} />
        {:else}
            <table class="w-full border-t border-border text-sm">
                <thead>
                    <tr class="border-b border-border">
                        <th
                            class="px-3 py-2 text-left text-xs font-medium tracking-wide text-muted-foreground uppercase"
                            >Meeting</th
                        >
                        <th
                            class="hidden px-3 py-2 text-left text-xs font-medium tracking-wide text-muted-foreground uppercase md:table-cell"
                            >Questions</th
                        >
                        <th
                            class="hidden px-3 py-2 text-left text-xs font-medium tracking-wide text-muted-foreground uppercase md:table-cell"
                            >Participants</th
                        >
                        <th
                            class="hidden px-3 py-2 text-left text-xs font-medium tracking-wide text-muted-foreground uppercase md:table-cell"
                            >Created</th
                        >
                        <th
                            class="px-3 py-2 text-right text-xs font-medium tracking-wide text-muted-foreground uppercase"
                            >Action</th
                        >
                    </tr>
                </thead>
                <tbody>
                    {#each filtered as meeting (meeting.id)}
                        <MeetingTableRow {meeting} />
                    {/each}
                </tbody>
            </table>
        {/if}
    </div>
</div>
