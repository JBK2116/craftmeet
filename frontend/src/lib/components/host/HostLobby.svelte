<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { MeetingIn } from '$lib/types/meeting';
    import type { Participant } from '$lib/types/participant';
    import { Clock, Copy, Hash, Play, Users } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';

    let {
        meeting,
        overallElapsed,
        participants,
        onstart,
        onopenparticipants,
    }: {
        meeting: MeetingIn;
        overallElapsed: number;
        participants: Participant[];
        onstart: () => void;
        onopenparticipants: () => void;
    } = $props();

    // Derived
    let totalDurationSecs = $derived(meeting.duration * 60);
    let progressPct = $derived(
        totalDurationSecs > 0 ? Math.min((overallElapsed / totalDurationSecs) * 100, 100) : 0,
    );
    let elapsedDisplay = $derived(formatTimer(overallElapsed));

    function formatTimer(seconds: number): string {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function copyRoomCode() {
        navigator.clipboard.writeText(meeting.room_code);
        toast.success('Room code copied!');
    }
</script>

<div class="mx-auto flex max-w-2xl flex-col items-center px-4 py-12">
    <!-- Room Code -->
    <div class="mb-8 flex flex-col items-center gap-2">
        <p class="text-sm font-medium text-muted-foreground">Room Code</p>
        <button
            onclick={copyRoomCode}
            class="group flex items-center gap-3 rounded-2xl border-2 border-primary/20 bg-primary/5 px-6 py-3 transition hover:border-primary/40 hover:bg-primary/10"
            aria-label="Copy room code"
        >
            <Hash class="h-5 w-5 text-primary/70" />
            <span class="text-3xl font-bold tracking-[0.25em] text-primary">
                {meeting.room_code}
            </span>
            <Copy class="h-4 w-4 text-muted-foreground transition group-hover:text-primary" />
        </button>
        <p class="text-xs text-muted-foreground">Share this code with participants to join</p>
    </div>

    <!-- Meeting Info -->
    <div class="mb-8 w-full text-center">
        <h1 class="text-2xl font-bold text-[var(--text-heading)]">{meeting.title}</h1>
        {#if meeting.description}
            <p class="mt-2 text-sm text-muted-foreground">{meeting.description}</p>
        {/if}
    </div>

    <!-- Timer & Progress -->
    <div class="mb-8 w-full max-w-md space-y-3">
        <div class="flex items-center justify-between text-sm">
            <div class="flex items-center gap-1.5 text-muted-foreground">
                <Clock class="h-4 w-4" />
                <span>Elapsed</span>
            </div>
            <span class="font-mono text-lg font-semibold tabular-nums">{elapsedDisplay}</span>
        </div>
        <div class="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
                class="h-full rounded-full bg-primary transition-all duration-1000 ease-linear"
                style="width: {progressPct}%"
            ></div>
        </div>
        <div class="flex justify-between text-xs text-muted-foreground">
            <span>0:00</span>
            <span>{meeting.duration}:00</span>
        </div>
    </div>

    <!-- Participants -->
    <div class="mb-8 w-full max-w-md">
        <button
            onclick={onopenparticipants}
            class="flex w-full items-center justify-between rounded-xl border border-border bg-card px-5 py-4 text-left transition-colors hover:bg-muted/50"
        >
            <div class="flex items-center gap-2 text-sm">
                <Users class="h-4 w-4 text-muted-foreground" />
                <span class="text-muted-foreground">Participants</span>
            </div>
            <span class="tabular-nums text-sm font-semibold text-foreground"
                >{participants.length}</span
            >
        </button>
    </div>

    <!-- Start Button -->
    <Button
        onclick={onstart}
        size="lg"
        class="gap-2 rounded-xl px-8 py-6 text-base font-semibold shadow-lg"
    >
        <Play class="h-5 w-5" />
        Start Meeting
    </Button>
</div>
