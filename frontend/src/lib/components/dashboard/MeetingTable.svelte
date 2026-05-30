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

<div>
    <!-- Filter tabs -->
    <div class="mb-4 flex gap-6 border-b border-border" role="tablist">
        {#each tabs as tab}
            <button
                role="tab"
                aria-selected={activeTab === tab}
                onclick={() => (activeTab = tab)}
                class="-mb-px border-b-2 pb-2 text-sm transition-colors {activeTab === tab
                    ? 'border-primary font-medium text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'}"
            >
                {tab}
            </button>
        {/each}
    </div>

    <!-- Meeting Table -->
    {#if filtered.length === 0}
        <EmptyState tab={activeTab} />
    {:else}
        <table class="w-full text-sm">
            <thead>
                <tr
                    class="border-b border-border text-xs font-medium tracking-wide text-muted-foreground uppercase"
                >
                    <th class="py-2 pr-3 text-left font-medium">Meeting</th>
                    <th class="hidden px-3 py-2 text-left font-medium md:table-cell">Questions</th>
                    <th class="hidden px-3 py-2 text-left font-medium md:table-cell"
                        >Participants</th
                    >
                    <th class="hidden px-3 py-2 text-left font-medium md:table-cell">Created</th>
                    <th class="py-2 pl-3 text-right font-medium">Action</th>
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
