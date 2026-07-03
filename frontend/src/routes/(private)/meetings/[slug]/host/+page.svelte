<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import HostLobby from '$lib/components/host/HostLobby.svelte';
    import HostParticipants from '$lib/components/host/HostParticipants.svelte';
    import HostQuestion from '$lib/components/host/HostQuestion.svelte';
    import { user } from '$lib/stores/stores';
    import type { LiveMeetingStatus } from '$lib/types/meeting';
    import type { Participant } from '$lib/types/participant';
    import type { QuestionIn, QuestionStatus } from '$lib/types/question';
    import type { ResponseOut } from '$lib/types/response';
    import { untrack } from 'svelte';
    import { toast } from 'svelte-sonner';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    // host info
    let hostUsername = $derived($user?.username ?? 'Unknown');
    let today = $state(
        new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
    );

    // root meeting object
    let meeting = $state(untrack(() => data.meeting));
    let meetingStatus = $state<LiveMeetingStatus>('lobby');

    // meeting questions logic
    let questions = $state<QuestionIn[]>(meeting.questions);
    let currQuestionIndex = $state(-1); // controls the question flow
    let currQuestion = $derived(questions[currQuestionIndex]);
    let currQuestionState = $derived<QuestionStatus>(currQuestion.status);
    let questionIsLast = $derived(currQuestionIndex === questions.length - 1);

    // meeting participants
    let participants = $state<Participant[]>([]);
    let showParticipants = $state(false);

    // responses
    let responses = $state<Record<string, ResponseOut[]>>({});

    // timer logic
    let start = $state<number | null>(null);
    let meetingEndTime = $state<Date | null>(null);
    let questionStart = $state<number | null>(null);
    let elapsedSeconds = $state<number>(0);
    let questionElapsed = $state<number>(0);

    // derived: status array for HostQuestion progress dots
    let questionStates = $derived(questions.map((q) => ({ status: q.status })));
    let currResponses = $derived(responses[currQuestion?.id] ?? []);
    let overallElapsed = $derived(elapsedSeconds);

    let endTimeDisplay = $derived(
        meetingEndTime
            ? meetingEndTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
            : null,
    );

    // timer effect
    $effect(() => {
        if (meetingStatus === 'lobby' && start === null) return;
        const timer = setInterval(() => {
            if (start !== null) {
                elapsedSeconds = Math.floor((Date.now() - start) / 1000);
            }
            if (questionStart !== null) {
                questionElapsed = Math.floor((Date.now() - questionStart) / 1000);
            }
        }, 1000);
        return () => clearInterval(timer);
    });

    /** Start the meeting */
    function handleStartMeeting() {
        start = Date.now();
        meetingEndTime = new Date(Date.now() + meeting.duration * 60 * 1000);
        meetingStatus = 'question';
        handleNextQuestion();
        // TODO: Send a message to the websocket
    }

    /** Proceed to the next question (advance, auto-open) */
    function handleNextQuestion() {
        if (!questionIsLast) {
            currQuestionIndex++;
        }
        // Auto-open the new current question
        if (currQuestion) {
            currQuestion.status = 'open';
            questionStart = Date.now();
        }
        // TODO: Send a message to the websocket
    }

    /** End the meeting. Sets the meeting status to 'ended' and notifies the host. */
    function handleEndMeeting() {
        meetingStatus = 'ended';
        toast.info('Meeting ended');
        // TODO: Send a message to the websocket
    }

    function handleReveal() {
        // TODO: implement reveal logic with websocket
    }

    //
    // WebSocket
    //

    type WsMessage = { type: string; payload: unknown };

    let ws = $state<WebSocket | null>(null);
    let wsConnected = $state(false);

    function getWsUrl(): string {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/api/v1/meetings/${page.params.slug}/host/ws`;
    }

    function handleWsMessage(msg: WsMessage) {
        switch (msg.type) {
            case 'participant_connected':
                handleParticipantConnected(msg.payload as Participant);
                break;
            case 'participant_disconnected':
                handleParticipantDisconnected(
                    (msg.payload as { participant_id: string }).participant_id,
                );
                break;
            case 'response':
                handleResponseReceived(msg.payload as ResponseOut);
                break;
            // TODO: add more message types as needed
            default:
                console.warn('[ws] unknown message type:', msg.type);
        }
    }

    function handleWsDisconnect(_event: CloseEvent) {
        console.warn('[ws] disconnected, attempting reconnect in 3s…');
        setTimeout(() => {
            if (browser && meetingStatus !== 'ended') {
                connectWs();
            }
        }, 3000);
    }

    function connectWs() {
        if (!browser) return;
        if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

        const socket = new WebSocket(getWsUrl());
        ws = socket;

        socket.onopen = () => {
            wsConnected = true;
        };

        socket.onmessage = (event: MessageEvent) => {
            try {
                const msg: WsMessage = JSON.parse(event.data);
                handleWsMessage(msg);
            } catch (err) {
                console.error('[ws] failed to parse message:', err);
            }
        };

        socket.onclose = (event: CloseEvent) => {
            wsConnected = false;
            handleWsDisconnect(event);
        };

        socket.onerror = (event: Event) => {
            console.error('[ws] error:', event);
        };
    }

    $effect(() => {
        connectWs();
        return () => {
            ws?.close();
            wsConnected = false;
        };
    });

    /**
     * Handle a participant connecting to the meeting.
     * Adds the participant to the list if new, or updates existing participant data.
     * @param participant - The participant data.
     */
    function handleParticipantConnected(participant: Participant) {
        let existingIndex = participants.findIndex((p) => p.id === participant.id);
        if (existingIndex === -1) {
            participants.push(participant);
        } else {
            participants[existingIndex] = participant;
        }
    }

    /**
     * Handle a participant disconnecting from the meeting.
     * Sets the participant's `connected` property to `false` if they exist in the list.
     * @param participant_id - The ID of the participant who disconnected.
     */
    function handleParticipantDisconnected(participant_id: string) {
        let existingIndex = participants.findIndex((p) => p.id == participant_id);
        if (existingIndex === -1) {
            return;
        }
        participants[existingIndex].connected = false;
    }

    /**
     * Handle a response received from a participant.
     * Marks the participant as having answered and stores the response.
     * @param response - The response data.
     */
    function handleResponseReceived(response: ResponseOut) {
        let pIndex = participants.findIndex((p) => p.id === response.participant_id);
        if (pIndex === -1) {
            return;
        }
        participants[pIndex].has_answered = true;
        const key = response.question_id;
        if (!responses[key]) {
            responses[key] = [];
        }
        responses[key].push(response);
    }
</script>

<!-- Persistent header -->
<div class="px-6 py-4">
    <div class="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
            <h1 class="truncate text-lg font-semibold text-[var(--text-heading)]">
                {meeting.title}
            </h1>
            {#if meeting.description}
                <p class="truncate text-sm text-muted-foreground">{meeting.description}</p>
            {/if}
        </div>
        <div class="flex items-center gap-4 text-sm text-muted-foreground">
            <button
                onclick={() => (showParticipants = true)}
                class="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 transition-colors hover:bg-muted"
            >
                <span class="tabular-nums font-medium text-foreground">{participants.length}</span>
                <span>participant{participants.length !== 1 ? 's' : ''}</span>
            </button>
            <span class="hidden h-4 w-px bg-border sm:block"></span>
            <span>{hostUsername}</span>
            {#if endTimeDisplay}
                <span class="hidden h-4 w-px bg-border sm:block"></span>
                <span class="hidden sm:inline">Ends at {endTimeDisplay}</span>
            {/if}
            <span class="hidden h-4 w-px bg-border sm:block"></span>
            <span class="hidden sm:inline">{today}</span>
        </div>
    </div>
</div>

<HostParticipants
    open={showParticipants}
    {participants}
    onclose={() => (showParticipants = false)}
/>

{#if meetingStatus === 'lobby'}
    <HostLobby
        {meeting}
        overallElapsed={0}
        {participants}
        onstart={handleStartMeeting}
        onopenparticipants={() => (showParticipants = true)}
    />
{:else if meetingStatus === 'question'}
    <HostQuestion
        {meeting}
        questionIndex={currQuestionIndex}
        {questionElapsed}
        questionState={currQuestionState}
        isLast={questionIsLast}
        totalQuestions={meeting.questions.length}
        participantCount={participants.length}
        {questionStates}
        responses={currResponses}
        onreveal={handleReveal}
        onnext={handleNextQuestion}
        onend={handleEndMeeting}
    />
{:else if meetingStatus === 'ended'}
    <div class="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 text-center">
        <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
            <svg
                class="h-10 w-10 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
        </div>
        <h1 class="mb-2 text-2xl font-bold text-[var(--text-heading)]">Meeting Ended</h1>
        <p class="mb-2 text-sm text-muted-foreground">
            Your meeting &ldquo;{meeting.title}&rdquo; has ended.
        </p>
        <p class="mb-8 text-sm text-muted-foreground">
            {participants.length} participant{participants.length !== 1 ? 's' : ''} &middot;
            {Math.floor(overallElapsed / 60)} min elapsed
        </p>
        <div class="flex gap-3">
            <button
                onclick={() => goto(`/meetings/${page.params.slug}`)}
                class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
                View Meeting Summary
            </button>
        </div>
    </div>
{/if}
