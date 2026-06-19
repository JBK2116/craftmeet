<script lang="ts">
    import LiveMeetingBanner from '$lib/components/dashboard/LiveMeetingBanner.svelte';
    import MeetingTable from '$lib/components/dashboard/MeetingTable.svelte';
    import QuickActions from '$lib/components/dashboard/QuickActions.svelte';
    import StatsBar from '$lib/components/dashboard/StatsBar.svelte';
    import { user } from '$lib/stores/stores';
    import type { MeetingIn } from '$lib/types/meeting';
    import { tick, untrack } from 'svelte';
    import { toast } from 'svelte-sonner';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    const meetings = $state(untrack(() => data.meetings as MeetingIn[]));
    const liveMeeting = $derived(meetings.find((m) => m.status === 'live'));

    // visual display functionality
    const greeting = $derived.by(() => {
        const hour = new Date().getHours();
        if (hour < 12) return 'morning';
        if (hour < 18) return 'afternoon';
        return 'evening';
    });
    const firstName = $derived($user?.username?.split(' ')[0] ?? 'there');

    // update effects
    $effect(() => {
        // remind the user to set their username for proper display in meetings
        if ($user && !$user.username) {
            tick().then(() => {
                toast.info(
                    'Your username is not set yet. Update it in your settings to personalize your meeting experience.',
                    { duration: Infinity },
                );
            });
        }
        // more effects go in here as needed
    });
</script>

<div class="mx-auto max-w-5xl space-y-5 px-4 py-6 md:px-6">
    <!-- Page header -->
    <header>
        <h2 class="text-lg font-semibold text-foreground">Dashboard</h2>
        <p class="text-sm text-muted-foreground">Good {greeting}, {firstName}</p>
    </header>
    <!-- Live Meeting Header -->
    {#if liveMeeting}
        <LiveMeetingBanner meeting={liveMeeting} />
    {/if}
    <!-- Main Page Body -->
    <StatsBar stats={$user!} />
    <QuickActions />
    <MeetingTable {meetings} />
</div>
