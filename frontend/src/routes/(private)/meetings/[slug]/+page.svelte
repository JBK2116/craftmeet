<script lang="ts">
    import type { MeetingIn } from '$lib/types/meeting';
    import { untrack } from 'svelte';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    let meeting: MeetingIn = $state(untrack(() => data.meeting as MeetingIn));
    $inspect(meeting)
</script>
