<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { refreshTokens } from '$lib/api/auth';
    import HostLobby from '$lib/components/host/HostLobby.svelte';
    import HostParticipants from '$lib/components/host/HostParticipants.svelte';
    import HostQuestion from '$lib/components/host/HostQuestion.svelte';
    import { user } from '$lib/stores/stores';
    import type { LiveMeetingStatus } from '$lib/types/meeting';
    import type { Participant } from '$lib/types/participant';
    import type { QuestionIn, QuestionStatus } from '$lib/types/question';
    import type { ResponseOut } from '$lib/types/response';
    import {
        CloseCode,
        type MeetingStartedPayload,
        type MeetingStatePayload,
        MessageTypes,
        type NextQuestionPayload,
        type ParticipantDisconnectedPayload,
        type ResponseReceivedPayload,
        type WebIn,
    } from '$lib/types/websocket';
    import { onMount, untrack } from 'svelte';
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

    // websocket logic
    let ws = $state<WebSocket | null>(null);
    let wsConnected = $state(false);
    let wsSuccessTimeout: ReturnType<typeof setTimeout> | null = null;
    let destroyed = false;
    let pendingEnd = $state(false);
    let endingMeeting = $state(false);
    let endTimeout: ReturnType<typeof setTimeout> | null = null;
    let isRevealed = $state(false);

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
        if (meetingStatus === 'ended') return;
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
        if (!wsConnected || !ws) return;
        if (meetingStatus !== 'lobby') return;
        start = Date.now();
        meetingEndTime = new Date(Date.now() + meeting.duration * 60 * 1000);
        meetingStatus = 'question';
        currQuestionIndex++;
        const question = questions[currQuestionIndex];
        // Auto-open the first question
        if (question) {
            question.status = 'open';
            questionStart = Date.now();
        }
        isRevealed = false;
        const payload = JSON.stringify({
            type: MessageTypes.MEETING_STARTED,
            payload: { question } as MeetingStartedPayload,
        });
        ws?.send(payload);
    }

    /** Proceed to the next question (advance, auto-open) */
    function handleNextQuestion() {
        if (!wsConnected || !ws) return;
        if (questionIsLast) return;
        currQuestionIndex++;
        isRevealed = false;
        // Auto-open the new current question
        if (currQuestion) {
            currQuestion.status = 'open';
            questionStart = Date.now();
        }
        const payload = JSON.stringify({
            type: MessageTypes.NEXT_QUESTION,
            payload: { question: currQuestion } as NextQuestionPayload,
        });
        ws?.send(payload);
    }

    /** End the meeting. Shows a confirmation before proceeding. */
    function handleEndMeeting() {
        pendingEnd = true;
    }

    function confirmEndMeeting() {
        pendingEnd = false;
        endingMeeting = true;
        const payload = JSON.stringify({ type: MessageTypes.MEETING_ENDED });
        ws?.send(payload);
        // small delay to let the backend finish post-meeting processing
        // (DB status update, user state, room cleanup) before navigating.
        endTimeout = setTimeout(() => {
            goto(`/meetings/${page.params.slug}`, { replaceState: true });
        }, 3000);
    }

    function cancelEndMeeting() {
        pendingEnd = false;
    }

    function handleReveal() {
        if (!wsConnected || !ws) return;
        isRevealed = true;
        ws?.send(JSON.stringify({ type: MessageTypes.REVEAL }));
    }

    function getWsUrl(): string {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/api/v1/meetings/${page.params.slug}/host/ws`;
    }

    /**
     * Handles incoming WebSocket messages by dispatching them to the appropriate handler.
     *
     * @param msg - The incoming WebSocket message containing a type and payload.
     * @param msg.type - The type of the message, used to determine the handler.
     * @param msg.payload - The payload data associated with the message.
     * @throws {Error} May throw if handlers receive unexpected payload shapes.
     */
    function handleWsMessage(msg: WebIn) {
        switch (msg.type) {
            case MessageTypes.PARTICIPANT_CONNECTED:
                handleParticipantConnected(msg.payload as Participant);
                break;
            case MessageTypes.PARTICIPANT_DISCONNECTED:
                handleParticipantDisconnected(msg.payload as ParticipantDisconnectedPayload);
                break;
            case MessageTypes.RESPONSE_RECEIVED:
                handleResponseReceived(msg.payload as ResponseReceivedPayload);
                break;
            case MessageTypes.MEETING_STATE:
                handleMeetingState(msg.payload as MeetingStatePayload);
                break;
            case MessageTypes.MEETING_ENDED:
                meetingStatus = 'ended';
                toast.info('Meeting time has expired.');
                break;
            // NOTE: add more message types as needed
            default:
                console.warn('[ws] unknown message type:', msg.type);
        }
    }

    /**
     * Handles WebSocket disconnection events.
     *
     * If the disconnection is due to a server rejection (codes 4001 or 1008),
     * it logs a warning, displays an error toast, and does not attempt to reconnect.
     * Otherwise, it logs a warning, shows a reconnection toast, and schedules
     * a reconnection attempt after 3 seconds, provided the meeting has not ended.
     *
     * @param event - The CloseEvent containing the disconnection code, reason, and details.
     */
    function handleWsDisconnect(event: CloseEvent) {
        if (destroyed) return;
        if (event.code === CloseCode.HOST_ALREADY_CONNECTED) {
            if (event.reason === 'invalid access token') {
                // Token expired mid-session — refresh and retry
                console.warn('[ws] access token invalid, refreshing and reconnecting…');
                refreshTokens().then((ok) => {
                    if (ok && !destroyed) {
                        connectWs();
                    } else {
                        toast.error('Your session has expired. Please log in again.');
                        goto('/login');
                    }
                });
                return;
            }
            console.warn('[ws] server rejected connection, not retrying:', event.reason);
            toast.error('Another host session is already active for this meeting. Redirecting…', {
                duration: 5000,
            });
            goto('/dashboard', { replaceState: true });
            return;
        }
        console.warn('[ws] disconnected, attempting reconnect in 3s…');
        if (meetingStatus !== 'ended') {
            toast.warning('Connection lost. Reconnecting…');
        }
        setTimeout(() => {
            if (browser && meetingStatus !== 'ended') {
                void connectWs();
            }
        }, 3000);
    }

    async function connectWs() {
        if (!browser) return;
        if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

        // refresh the access token before opening the WebSocket so the
        // cookie is valid when the server authenticates the connection.
        const refreshed = await refreshTokens();
        if (!refreshed) {
            toast.error('Your session has expired. Please log in again.');
            goto('/login');
            return;
        }

        const socket = new WebSocket(getWsUrl());
        ws = socket;

        socket.onopen = () => {
            wsConnected = true;
            // Delay success toast to avoid race with immediate server rejection
            wsSuccessTimeout = setTimeout(() => {
                toast.success('Connected to meeting');
            }, 500);
        };

        socket.onmessage = (event: MessageEvent) => {
            try {
                const msg: WebIn = JSON.parse(event.data);
                handleWsMessage(msg);
            } catch (err) {
                console.error('[ws] failed to parse message:', err);
            }
        };

        socket.onclose = (event: CloseEvent) => {
            wsConnected = false;
            if (wsSuccessTimeout) {
                clearTimeout(wsSuccessTimeout);
                wsSuccessTimeout = null;
            }
            handleWsDisconnect(event);
        };

        socket.onerror = (event: Event) => {
            console.error('[ws] error:', event);
            toast.error('Connection error');
        };
    }

    onMount(() => {
        void connectWs();
        return () => {
            destroyed = true;
            ws?.close();
            wsConnected = false;
            if (wsSuccessTimeout) {
                clearTimeout(wsSuccessTimeout);
                wsSuccessTimeout = null;
            }
            if (endTimeout) {
                clearTimeout(endTimeout);
                endTimeout = null;
            }
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
     * @param payload - The payload with the data of the disconnecting participant
     */
    function handleParticipantDisconnected(payload: ParticipantDisconnectedPayload) {
        let existingIndex = participants.findIndex((p) => p.id === payload.id);
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
    function handleResponseReceived(payload: ResponseReceivedPayload) {
        let pIndex = participants.findIndex((p) => p.id === payload.response.participant_id);
        if (pIndex === -1) {
            return;
        }
        participants[pIndex].has_answered = true;
        const key = payload.response.question_id;
        if (!responses[key]) {
            responses[key] = [];
        }
        responses[key].push(payload.response);
        // If currently revealing, push updated responses to participants
        if (isRevealed) {
            ws?.send(JSON.stringify({ type: MessageTypes.REVEAL }));
        }
    }

    /**
     * Handles the state of a meeting by updating responses, participants, and the current question.
     * @param payload - The meeting state payload containing responses, participants, and optionally a question.
     */
    function handleMeetingState(payload: MeetingStatePayload) {
        // Store responses keyed by question ID (responses is a $state Record, not a derived)
        if (payload.question) {
            responses[payload.question.id] = payload.responses;
        }
        participants = payload.participants;
        if (!payload.question) {
            return;
        }
        // Update the question in the questions array so the derived picks it up
        const questionIndex = questions.findIndex((f) => f.id === payload.question!.id);
        if (questionIndex === -1) return;
        questions[questionIndex] = payload.question;
        currQuestionIndex = questionIndex;
        // Meeting is already in progress — transition from lobby to question
        if (meetingStatus === 'lobby') {
            meetingStatus = 'question';
            // Recalculate timing from the DB-persisted started_at so the host
            // sees the correct elapsed time and end-time display on reconnect.
            if (meeting.started_at) {
                const startedTimestamp = new Date(meeting.started_at).getTime();
                start = startedTimestamp;
                meetingEndTime = new Date(startedTimestamp + meeting.duration * 60 * 1000);
            } else {
                start = Date.now();
                meetingEndTime = new Date(Date.now() + meeting.duration * 60 * 1000);
            }
            questionStart = Date.now();
        }
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
                class="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-mono font-medium text-primary cursor-pointer select-all"
                title="Click to copy"
                onclick={() => {
                    navigator.clipboard.writeText(meeting.room_code);
                    toast.success('Code copied');
                }}
            >
                {meeting.room_code}
            </button>
            <span class="hidden h-4 w-px bg-border sm:block"></span>
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
        {isRevealed}
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
                onclick={() => goto(`/meetings/${page.params.slug}/summary`)}
                class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
                View Meeting Summary
            </button>
        </div>
    </div>
{/if}

{#if endingMeeting}
    <div
        class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm"
    >
        <div class="flex flex-col items-center gap-4">
            <div
                class="h-8 w-8 rounded-full border-2 border-muted border-t-primary animate-spin"
            ></div>
            <p class="text-sm text-muted-foreground">Ending meeting…</p>
        </div>
    </div>
{:else if pendingEnd}
    <!-- End Meeting confirmation overlay -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
        <div
            class="mx-4 w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-overlay"
        >
            <h3 class="mb-2 text-lg font-semibold text-[var(--text-heading)]">End Meeting?</h3>
            <p class="mb-6 text-sm text-muted-foreground">
                This will end the meeting for all participants. This action cannot be undone.
            </p>
            <div class="flex gap-3">
                <button
                    onclick={cancelEndMeeting}
                    class="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    Cancel
                </button>
                <button
                    onclick={confirmEndMeeting}
                    class="flex-1 rounded-xl bg-destructive px-4 py-2.5 text-sm font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    End Meeting
                </button>
            </div>
        </div>
    </div>
{/if}
