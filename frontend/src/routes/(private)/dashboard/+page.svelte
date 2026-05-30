<script lang="ts">
    import LiveMeetingBanner from '$lib/components/dashboard/LiveMeetingBanner.svelte';
    import MeetingTable from '$lib/components/dashboard/MeetingTable.svelte';
    import QuickActions from '$lib/components/dashboard/QuickActions.svelte';
    import StatsBar from '$lib/components/dashboard/StatsBar.svelte';
    import { mockMeetings, mockUser } from '$lib/types/mock';

    // swap these for a real `load()` function once the API is wired.
    const user = mockUser;
    const meetings = mockMeetings;
    // find the live meeting if it exists
    const liveMeeting = $derived(meetings.find((m) => m.status === 'live'));

    const greeting = $derived.by(() => {
        const hour = new Date().getHours();
        if (hour < 12) return 'morning';
        if (hour < 18) return 'afternoon';
        return 'evening';
    });

    const firstName = $derived(user.name.split(' ')[0]);
</script>

<div class="mx-auto max-w-5xl space-y-6 px-4 py-6 md:px-6">
    <!-- Page header -->
    <header>
        <h1>Dashboard</h1>
        <p class="text-meta">Good {greeting}, {firstName}</p>
    </header>
    <!-- Live Meeting Header -->
    {#if liveMeeting}
        <LiveMeetingBanner meeting={liveMeeting} />
    {/if}
    <!-- Main Page Body -->
    <StatsBar stats={user} />
    <QuickActions />
    <MeetingTable {meetings} />
</div>
