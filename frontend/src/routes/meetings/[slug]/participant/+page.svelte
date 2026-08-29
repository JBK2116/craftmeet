<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import ChatBar from '$lib/components/chat/ChatBar.svelte';
    import HostParticipants from '$lib/components/host/HostParticipants.svelte';
    import { Button } from '$lib/components/ui/button';
    import type { Participant } from '$lib/types/participant';
    import type {
        LongAnswerQuestionIn,
        MultipleChoiceQuestionIn,
        QuestionIn,
        RankedVotingQuestionIn,
        RatingScaleQuestionIn,
    } from '$lib/types/question';
    import type {
        LongAnswerResponseOut,
        MultipleChoiceResponseOut,
        RankedVotingResponseOut,
        RatingScaleResponseOut,
        ResponseOut,
        YesNoResponseOut,
    } from '$lib/types/response';
    import {
        type ChatMessage,
        type ChatReceivedPayload,
        type ChatStatePayload,
        CloseCode,
        type CurrentQuestionPayload,
        type MeetingStartedPayload,
        MessageTypes,
        type NextQuestionPayload,
        type ParticipantDisconnectedPayload,
        type ParticipantJoinRoomFailed,
        type ParticipantJoinRoomSuccess,
        type ParticipantsStatePayload,
        type RevealMeetingPayload,
        type WebIn,
    } from '$lib/types/websocket';
    import { MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH } from '$lib/utils/constants';
    import { UserX, Users } from '@lucide/svelte';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';

    // Participant state sourced from server messages
    let username = $state('');
    let participantId = $state<string | null>(null);
    let isLobby = $state(false);
    let joiningRoom = $state(false);

    // Chat
    let chats = $state<ChatMessage[]>([]);

    // Participants (populated when backend adds a participant-list message)
    let participants = $state<Participant[]>([]);
    let chatOpen = $state(false);
    let participantsOpen = $state(false);

    // Meeting state
    let phase = $state<
        | 'connecting'
        | 'waiting'
        | 'question'
        | 'answered'
        | 'revealed'
        | 'host_disconnected'
        | 'kicked'
        | 'ended'
    >('connecting');
    let currentQuestion = $state<QuestionIn | null>(null);
    let revealedResponses = $state<ResponseOut[]>([]);
    let hasAnswered = $state(false);
    let hasLeft = false;
    // Highest question position seen so far, used to render a progress bar.
    let highestPosition = $state(0);

    /** Call the leave endpoint once to clear the participant cookie. */
    function leaveMeeting() {
        if (hasLeft) return;
        hasLeft = true;
        fetch(`/api/v1/meetings/${page.params.slug}/leave`, {
            method: 'POST',
            credentials: 'include',
        }).catch(() => {});
    }

    // Reveal aggregations
    let totalResp = $derived(revealedResponses.length);

    let mcCounts = $derived.by(() => {
        if (!currentQuestion || currentQuestion.type !== 'multiple_choice') return [];
        const counts: number[] = [];
        for (const r of revealedResponses as MultipleChoiceResponseOut[]) {
            for (const o of r.selected_options) {
                counts[o] = (counts[o] ?? 0) + 1;
            }
        }
        return counts;
    });

    let ratingAvg = $derived.by(() => {
        if (
            !currentQuestion ||
            currentQuestion.type !== 'rating_scale' ||
            revealedResponses.length === 0
        )
            return null;
        const vals = (revealedResponses as RatingScaleResponseOut[]).map((r) => r.value);
        return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
    });

    let yesNoCounts = $derived.by(() => {
        if (!currentQuestion || currentQuestion.type !== 'yes_no') return null;
        const yes = (revealedResponses as YesNoResponseOut[]).filter((r) => r.value).length;
        return { yes, no: revealedResponses.length - yes, total: revealedResponses.length };
    });

    let rankedFirst = $derived.by(() => {
        if (!currentQuestion || currentQuestion.type !== 'ranked_voting') return [];
        const counts: number[] = [0, 0, 0, 0];
        for (const r of revealedResponses as RankedVotingResponseOut[]) {
            if (r.rank_1 === 1) counts[0]++;
            if (r.rank_2 === 1) counts[1]++;
            if (r.rank_3 === 1) counts[2]++;
            if (r.rank_4 === 1) counts[3]++;
        }
        return counts;
    });

    let longAnswers = $derived.by(() => {
        if (!currentQuestion || currentQuestion.type !== 'long_answer') return [];
        return (revealedResponses as LongAnswerResponseOut[]).map((r) => r.content);
    });

    // Answer input state — varies by question type
    let mcSelected = $state<number[]>([]);
    let longAnswerText = $state('');
    let rankedRanks = $state<{
        rank_1: number;
        rank_2: number;
        rank_3: number | null;
        rank_4: number | null;
    }>({ rank_1: 1, rank_2: 2, rank_3: 3, rank_4: 4 });
    let ratingValue = $state<number>(0);
    let yesNoValue = $state<boolean | null>(null);

    // WebSocket
    let ws = $state<WebSocket | null>(null);
    let wsConnected = $state(false);
    let destroyed = false;
    let reconnectAttempts = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatInterval: ReturnType<typeof setInterval> | null = null;
    let missedPongs = 0;
    const MAX_RECONNECT_ATTEMPTS = 4;
    const HEARTBEAT_INTERVAL_MS = 20_000;
    const MAX_MISSED_PONGS = 2;

    /** Build the WebSocket URL for the participant connection to this meeting. */
    function getWsUrl(): string {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/api/v1/meetings/${page.params.slug}/participant/ws`;
    }

    /** Reset all answer input state to defaults, called when moving to a new question. */
    function resetAnswerState() {
        mcSelected = [];
        longAnswerText = '';
        rankedRanks = { rank_1: 1, rank_2: 2, rank_3: 3, rank_4: 4 };
        ratingValue = 0;
        yesNoValue = null;
        hasAnswered = false;
        revealedResponses = [];
    }

    /**
     * Build and send the appropriate response payload based on the current question type.
     *
     * Guards against missing WebSocket connection, current question, or participant ID.
     * After sending, transitions the phase to `'answered'`.
     */
    function submitAnswer() {
        if (!ws || !wsConnected || !currentQuestion || !participantId) return;

        let response: ResponseOut;
        const qType = currentQuestion.type;

        switch (qType) {
            case 'multiple_choice':
                if (mcSelected.length === 0) return;
                response = {
                    type: 'multiple_choice',
                    question_id: currentQuestion.id,
                    participant_id: participantId,
                    selected_options: mcSelected,
                } as MultipleChoiceResponseOut;
                break;
            case 'long_answer':
                if (!longAnswerText.trim()) return;
                response = {
                    type: 'long_answer',
                    question_id: currentQuestion.id,
                    participant_id: participantId,
                    content: longAnswerText.trim(),
                };
                break;
            case 'ranked_voting':
                response = {
                    type: 'ranked_voting',
                    question_id: currentQuestion.id,
                    participant_id: participantId,
                    rank_1: rankedRanks.rank_1,
                    rank_2: rankedRanks.rank_2,
                    rank_3: rankedRanks.rank_3,
                    rank_4: rankedRanks.rank_4,
                } as RankedVotingResponseOut;
                break;
            case 'rating_scale':
                if (ratingValue === 0) return;
                response = {
                    type: 'rating_scale',
                    question_id: currentQuestion.id,
                    participant_id: participantId,
                    value: ratingValue,
                } as RatingScaleResponseOut;
                break;
            case 'yes_no':
                if (yesNoValue === null) return;
                response = {
                    type: 'yes_no',
                    question_id: currentQuestion.id,
                    participant_id: participantId,
                    value: yesNoValue,
                } as YesNoResponseOut;
                break;
            default:
                return;
        }

        ws.send(JSON.stringify({ type: MessageTypes.RESPONSE_RECEIVED, payload: { response } }));
        hasAnswered = true;
        // If the host already revealed while we were answering, go straight to revealed
        phase = revealedResponses.length > 0 ? 'revealed' : 'answered';
    }

    /** Send the participant's chosen name to leave the lobby and enter the meeting. */
    function joinRoom() {
        const name = username.trim();
        if (name.length < MIN_USERNAME_LENGTH || name.length > MAX_USERNAME_LENGTH) {
            toast.error(
                `Your name must be between ${MIN_USERNAME_LENGTH} and ${MAX_USERNAME_LENGTH} characters.`,
            );
            return;
        }
        if (!ws || !wsConnected || ws.readyState !== WebSocket.OPEN) return;
        joiningRoom = true;
        ws.send(
            JSON.stringify({
                type: MessageTypes.PARTICIPANT_JOIN_ROOM,
                payload: { username: name },
            }),
        );
    }

    /**
     * Handles incoming WebSocket messages by dispatching them to the appropriate state update.
     *
     * @param msg - The incoming WebSocket message containing a type and payload.
     */
    function handleWsMessage(msg: WebIn) {
        switch (msg.type) {
            case MessageTypes.PARTICIPANT_STATE: {
                const p = msg.payload as Participant;
                participantId = p.id;
                username = p.username ?? '';
                hasAnswered = p.has_answered;
                isLobby = p.is_lobby;
                if (phase === 'connecting') {
                    phase = 'waiting';
                } else if (phase === 'question' && hasAnswered) {
                    phase = 'answered';
                }
                break;
            }
            case MessageTypes.PARTICIPANT_JOIN_ROOM_SUCCESS: {
                const payload = msg.payload as ParticipantJoinRoomSuccess;
                const p = payload.participant;
                participantId = p.id;
                username = p.username ?? '';
                hasAnswered = p.has_answered;
                isLobby = p.is_lobby;
                joiningRoom = false;
                phase = currentQuestion ? (hasAnswered ? 'answered' : 'question') : 'waiting';
                break;
            }
            case MessageTypes.PARTICIPANT_JOIN_ROOM_FAILED: {
                const payload = msg.payload as ParticipantJoinRoomFailed;
                joiningRoom = false;
                toast.error(payload.detail);
                break;
            }
            case MessageTypes.PARTICIPANT_CONNECTED: {
                handleParticipantConnected(msg.payload as Participant);
                return;
            }
            case MessageTypes.PARTICIPANT_DISCONNECTED: {
                handleParticipantDisconnected(msg.payload as ParticipantDisconnectedPayload);
                return;
            }
            case MessageTypes.PARTICIPANTS_STATE: {
                handleParticipantsState(msg.payload as ParticipantsStatePayload);
                return;
            }
            case MessageTypes.CURRENT_QUESTION: {
                const payload = msg.payload as CurrentQuestionPayload;
                currentQuestion = payload.question;
                highestPosition = Math.max(highestPosition, payload.question.position);
                // On (re)connect the server snapshot is authoritative: drop any stale
                // reveal data from before the disconnect. If the host had already
                // revealed, the backend follows CURRENT_QUESTION with a fresh REVEAL,
                // so revealedResponses is repopulated right after (not lost).
                revealedResponses = [];
                // Don't reset answer state — CURRENT_QUESTION is only sent on
                // connect/reconnect (not a new question). PARTICIPANT_STATE
                // (sent alongside) provides the authoritative has_answered value.
                phase = hasAnswered ? 'answered' : 'question';
                break;
            }
            case MessageTypes.MEETING_STARTED: {
                const payload = msg.payload as MeetingStartedPayload;
                currentQuestion = payload.question;
                highestPosition = Math.max(highestPosition, payload.question.position);
                resetAnswerState();
                phase = 'question';
                break;
            }
            case MessageTypes.NEXT_QUESTION: {
                const payload = msg.payload as NextQuestionPayload;
                currentQuestion = payload.question;
                highestPosition = Math.max(highestPosition, payload.question.position);
                resetAnswerState();
                phase = 'question';
                break;
            }
            case MessageTypes.CHAT_RECEIVED: {
                handleChatReceived(msg.payload as ChatReceivedPayload);
                break;
            }
            case MessageTypes.CHAT_STATE: {
                handleChatState(msg.payload as ChatStatePayload);
                break;
            }
            case MessageTypes.REVEAL: {
                const payload = msg.payload as RevealMeetingPayload;
                revealedResponses = payload.responses;
                // Only show reveal if already answered; late participants stay on question
                if (hasAnswered) phase = 'revealed';
                break;
            }
            case MessageTypes.HOST_DISCONNECTED:
                phase = 'host_disconnected';
                toast.warning('Host has disconnected. Waiting for them to return…');
                break;
            case MessageTypes.HOST_RECONNECTED:
                if (phase === 'host_disconnected') {
                    phase = currentQuestion ? 'question' : 'waiting';
                }
                toast.success('Host has returned.');
                break;
            case MessageTypes.MEETING_ENDED:
                phase = 'ended';
                isLobby = false;
                toast.info('The meeting has ended.');
                leaveMeeting();
                break;
            case MessageTypes.PONG:
                missedPongs = 0;
                break;
            default:
                console.warn('[ws] unknown message type:', msg.type);
        }
    }

    /** Append the incoming chat to the chat bar */
    function handleChatReceived(payload: ChatReceivedPayload) {
        chats.push(payload.chat);
        return;
    }

    /** Update the chats state to match the incoming server state */
    function handleChatState(payload: ChatStatePayload) {
        chats = [];
        chats.push(...payload.chats);
        return;
    }

    /** Send the chat message to the backend if the message is valid */
    function handleChatSend(message: string) {
        if (message.length < 1 || message.length > 255) {
            toast.error('Chat message must be between 1 and 255 characters.');
            return;
        }
        if (!participantId || username.length === 0) {
            return; // participant will have to wait to receive their id and a proper username first
        }
        if (!wsConnected || !ws || ws.readyState !== WebSocket.OPEN) {
            return;
        }
        const chatMessage = {
            name: username,
            u_id: participantId,
            message: message,
            is_host: false,
        } as ChatMessage;
        const payload = { type: MessageTypes.CHAT_RECEIVED, payload: { chat: chatMessage } };
        ws.send(JSON.stringify(payload));
    }

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

    /** Update the participants array to match the backend server state */
    function handleParticipantsState(payload: ParticipantsStatePayload) {
        participants = [];
        participants.push(...payload.participants);
        return;
    }

    /** Stop and detach the heartbeat interval, if one is running. */
    function clearHeartbeat() {
        if (heartbeatInterval !== null) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
        missedPongs = 0;
    }

    /** Schedule a reconnect with exponential backoff + jitter, or give up after max attempts. */
    function scheduleReconnect() {
        if (reconnectTimer !== null) return;

        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.warn('[ws] giving up after reconnection attempts');
            leaveMeeting();
            toast.error('Unable to connect to meeting.', { duration: Infinity });
            goto('/', { replaceState: true });
            return;
        }

        const delay = Math.min(1000 * 2 ** reconnectAttempts, 15_000) + Math.random() * 1000;
        reconnectAttempts++;

        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            // Guard against unmount during the wait - don't reconnect after teardown.
            if (!destroyed && browser && phase !== 'ended') {
                void connectWs();
            }
        }, delay);
    }

    /**
     * Handles WebSocket disconnection events.
     *
     * If the disconnection is due to a duplicate tab or invalid/expired token,
     * it displays an error toast and does not attempt to reconnect.
     * Otherwise, it shows a warning toast and schedules a reconnection attempt
     * with exponential backoff, provided the meeting has not ended.
     *
     * @param event - The CloseEvent containing the disconnection code and reason.
     */
    function handleWsDisconnect(event: CloseEvent) {
        clearHeartbeat();
        if (destroyed) return;
        joiningRoom = false;
        if (event.code === CloseCode.MEETING_NOT_FOUND) {
            toast.error('Unable to join meeting. Please check your link and try again.', {
                duration: Infinity,
            });
            goto('/', { replaceState: true });
            return;
        }
        if (event.code === CloseCode.PARTICIPANT_RECONNECTED_ELSEWHERE) {
            toast.error(
                'You joined this meeting from another tab. This connection is now closed.',
                { duration: 6000 },
            );
            return;
        }
        if (event.code === CloseCode.INVALID_TOKEN) {
            toast.error('Your session has expired. Please rejoin the meeting.', { duration: 6000 });
            goto('/', { replaceState: true });
            return;
        }
        if (event.code === CloseCode.PARTICIPANT_KICKED_FROM_MEETING) {
            // Do not reconnect or clear the participant cookie: the cookie
            // carries the banned identity, so the server keeps rejecting it.
            phase = 'kicked';
            isLobby = false;
            return;
        }
        if (event.code === CloseCode.MEETING_IS_FULL) {
            toast.error('This meeting has reached its participant limit.', { duration: Infinity });
            goto('/', { replaceState: true });
            return;
        }
        if (phase !== 'ended') {
            toast.warning('Connection lost. Reconnecting…');
        }
        scheduleReconnect();
    }

    /**
     * Establish (or re-establish) the WebSocket connection to the meeting.
     *
     * Skips if not in a browser environment or if a connection is already open.
     * On open, sends a `participant_connected` message to register with the server
     * and starts the heartbeat interval.
     */
    async function connectWs() {
        if (!browser) return;
        if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

        const socket = new WebSocket(getWsUrl());
        ws = socket;

        socket.onopen = () => {
            wsConnected = true;
            reconnectAttempts = 0;
            // send participant_connected message with the meeting id
            socket.send(
                JSON.stringify({
                    type: MessageTypes.PARTICIPANT_CONNECTED,
                    payload: { meeting_id: page.params.slug },
                }),
            );

            // Start the heartbeat: ping every ~20s, force-close if pongs are missed.
            // NOTE: this requires the backend to echo PING messages back as PONG.
            //       The server side of this handshake is intentionally not implemented here.
            clearHeartbeat();
            missedPongs = 0;
            heartbeatInterval = setInterval(() => {
                if (socket.readyState !== WebSocket.OPEN) return;
                missedPongs++;
                if (missedPongs > MAX_MISSED_PONGS) {
                    console.warn('[ws] missed too many pongs, forcing reconnect');
                    socket.close();
                    return;
                }
                socket.send(JSON.stringify({ type: MessageTypes.PING }));
            }, HEARTBEAT_INTERVAL_MS);
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
            clearHeartbeat();
            handleWsDisconnect(event);
        };

        socket.onerror = (event: Event) => {
            console.error('[ws] error:', event);
            toast.error('Connection error');
        };
    }

    onMount(() => {
        // Reconnect when the tab becomes visible again or the network returns.
        const handleVisibility = () => {
            if (document.visibilityState === 'visible') {
                if (ws?.readyState !== WebSocket.OPEN && !destroyed && phase !== 'kicked') {
                    void connectWs();
                }
            }
        };
        const handleOnline = () => {
            if (ws?.readyState !== WebSocket.OPEN && !destroyed && phase !== 'kicked') {
                void connectWs();
            }
        };
        document.addEventListener('visibilitychange', handleVisibility);
        window.addEventListener('online', handleOnline);

        void connectWs();

        return () => {
            destroyed = true;
            document.removeEventListener('visibilitychange', handleVisibility);
            window.removeEventListener('online', handleOnline);
            if (reconnectTimer !== null) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            clearHeartbeat();
            ws?.close();
            wsConnected = false;
        };
    });
</script>

{#if isLobby}
    <div class="flex min-h-[calc(100vh-56px)] items-center justify-center px-4">
        <div class="w-full max-w-sm rounded-2xl border border-border bg-card p-6">
            <div class="mb-6 text-center">
                <div
                    class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10"
                >
                    <Users class="h-6 w-6 text-primary" />
                </div>
                <h1 class="mb-2 text-xl font-semibold text-(--text-heading)">Join the meeting</h1>
                <p class="text-sm text-muted-foreground">Enter your name to join the meeting.</p>
            </div>
            <div class="flex flex-col gap-3">
                <input
                    type="text"
                    placeholder="Your name"
                    maxlength={MAX_USERNAME_LENGTH}
                    bind:value={username}
                    disabled={joiningRoom}
                    onkeydown={(e) => e.key === 'Enter' && joinRoom()}
                    class="h-10 w-full rounded-lg border border-border bg-background px-4 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20"
                />
                <button
                    onclick={joinRoom}
                    disabled={joiningRoom}
                    class="h-10 w-full rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                    {#if joiningRoom}
                        <div
                            class="mx-auto h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin"
                        ></div>
                    {:else}
                        Join Meeting
                    {/if}
                </button>
            </div>
        </div>
    </div>
{:else}
    <div class="grid lg:grid-cols-[1fr_320px] h-[calc(100vh-56px)] overflow-hidden">
        <!-- Main content area -->
        <div class="overflow-y-auto">
            <!-- Mobile header -->
            <div
                class="flex items-center justify-between border-b border-border px-4 py-3 lg:hidden"
            >
                <span class="text-sm font-medium text-muted-foreground">{username}</span>
                <div class="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onclick={() => (participantsOpen = true)}>
                        <Users class="size-5" />
                    </Button>
                    <ChatBar variant="sheet" bind:open={chatOpen} {chats} onsend={handleChatSend} />
                </div>
            </div>

            <div class="mx-auto max-w-2xl px-4 py-10">
                {#if phase === 'connecting'}
                    <div class="flex flex-col items-center py-20">
                        <div
                            class="h-8 w-8 rounded-full border-2 border-muted border-t-primary animate-spin"
                        ></div>
                        <p class="mt-4 text-sm text-muted-foreground">Connecting to meeting…</p>
                    </div>
                {:else if phase === 'waiting'}
                    <div class="flex flex-col items-center py-20 text-center">
                        <div
                            class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10"
                        >
                            <span class="relative flex h-4 w-4">
                                <span
                                    class="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"
                                ></span>
                                <span class="relative inline-flex h-4 w-4 rounded-full bg-primary"
                                ></span>
                            </span>
                        </div>
                        <h1 class="mb-2 text-2xl font-bold text-(--text-heading)">You're in!</h1>
                        <p class="text-sm text-muted-foreground">
                            Joined as <span class="font-medium text-foreground">{username}</span>.
                            Waiting for the host to start the meeting…
                        </p>
                        <div
                            class="mt-6 flex items-center gap-3 rounded-full border border-border bg-card px-4 py-1.5 text-xs text-muted-foreground"
                        >
                            <Users class="h-3.5 w-3.5" />
                            <span>{participants.length} waiting</span>
                        </div>
                    </div>
                {:else if phase === 'question' && currentQuestion}
                    <div class="space-y-6">
                        <!-- Question header -->
                        <div class="rounded-2xl border border-border bg-card p-6">
                            <span
                                class="inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
                            >
                                Question {currentQuestion.position}
                            </span>
                            <h2 class="mt-3 text-xl font-semibold text-(--text-heading)">
                                {currentQuestion.prompt}
                            </h2>
                            {#if highestPosition > 1}
                                <div class="mt-4 flex items-center gap-1.5">
                                    {#each Array.from({ length: highestPosition }) as _, i}
                                        {@const pos = i + 1}
                                        <span
                                            class="h-1.5 flex-1 rounded-full transition-colors {pos <=
                                            currentQuestion.position
                                                ? 'bg-primary'
                                                : 'bg-muted'}"
                                        ></span>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                        <!-- Answer input by type -->
                        <div class="rounded-2xl border border-border bg-card p-6">
                            {#if currentQuestion.type === 'multiple_choice'}
                                {@const sub =
                                    currentQuestion.sub_question as MultipleChoiceQuestionIn}
                                <div class="space-y-3">
                                    {#each [sub.option_1, sub.option_2, sub.option_3, sub.option_4].filter(Boolean) as option, i}
                                        <label
                                            class="flex items-center gap-3 rounded-xl border p-4 cursor-pointer transition-colors hover:bg-accent {mcSelected.includes(
                                                i + 1,
                                            )
                                                ? 'border-primary bg-primary/5'
                                                : 'border-border'}"
                                        >
                                            {#if sub.allow_multiple}
                                                <input
                                                    type="checkbox"
                                                    class="h-4 w-4 rounded accent-primary"
                                                    checked={mcSelected.includes(i + 1)}
                                                    onchange={(e) => {
                                                        const checked = e.currentTarget.checked;
                                                        if (checked) {
                                                            mcSelected = [...mcSelected, i + 1];
                                                        } else {
                                                            mcSelected = mcSelected.filter(
                                                                (v) => v !== i + 1,
                                                            );
                                                        }
                                                    }}
                                                />
                                            {:else}
                                                <input
                                                    type="radio"
                                                    name="mc"
                                                    class="h-4 w-4 accent-primary"
                                                    checked={mcSelected.includes(i + 1)}
                                                    onchange={() => {
                                                        mcSelected = [i + 1];
                                                    }}
                                                />
                                            {/if}
                                            <span class="text-sm text-foreground">{option}</span>
                                        </label>
                                    {/each}
                                </div>
                            {:else if currentQuestion.type === 'long_answer'}
                                {@const sub = currentQuestion.sub_question as LongAnswerQuestionIn}
                                <textarea
                                    bind:value={longAnswerText}
                                    maxlength={sub.max_length}
                                    rows={4}
                                    placeholder="Type your answer…"
                                    class="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20 resize-none"
                                ></textarea>
                                <p class="mt-2 text-xs text-muted-foreground text-right">
                                    {longAnswerText.length}/{sub.max_length}
                                </p>
                            {:else if currentQuestion.type === 'ranked_voting'}
                                {@const sub =
                                    currentQuestion.sub_question as RankedVotingQuestionIn}
                                {@const items = [
                                    sub.item_1,
                                    sub.item_2,
                                    sub.item_3,
                                    sub.item_4,
                                ].filter(Boolean)}
                                <p class="mb-3 text-sm text-muted-foreground">
                                    Rank the following items (1 = best):
                                </p>
                                <div class="space-y-3">
                                    {#each items as item, i}
                                        <div
                                            class="flex items-center gap-3 rounded-xl border border-border p-4"
                                        >
                                            <span class="text-sm font-medium text-foreground flex-1"
                                                >{item}</span
                                            >
                                            <select
                                                class="h-9 rounded-lg border border-border bg-background py-2 pl-3 pr-8 text-sm text-foreground outline-none focus:border-primary/40 appearance-none bg-no-repeat"
                                                style="background-image: url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22%2F%3E%3C%2Fsvg%3E'); background-position: right 0.5rem center; background-size: 1rem;"
                                                value={i === 0
                                                    ? rankedRanks.rank_1
                                                    : i === 1
                                                      ? rankedRanks.rank_2
                                                      : i === 2
                                                        ? (rankedRanks.rank_3 ?? '')
                                                        : (rankedRanks.rank_4 ?? '')}
                                                onchange={(e) => {
                                                    const newVal = e.currentTarget.value
                                                        ? parseInt(e.currentTarget.value)
                                                        : null;
                                                    const oldVal =
                                                        i === 0
                                                            ? rankedRanks.rank_1
                                                            : i === 1
                                                              ? rankedRanks.rank_2
                                                              : i === 2
                                                                ? rankedRanks.rank_3
                                                                : rankedRanks.rank_4;
                                                    // Prevent duplicate ranks: if another item already
                                                    // has this rank, swap values.
                                                    if (newVal !== null && oldVal !== null) {
                                                        const conflictIdx = [
                                                            rankedRanks.rank_1,
                                                            rankedRanks.rank_2,
                                                            rankedRanks.rank_3,
                                                            rankedRanks.rank_4,
                                                        ].findIndex(
                                                            (r, idx) => idx !== i && r === newVal,
                                                        );
                                                        if (conflictIdx !== -1) {
                                                            if (conflictIdx === 0)
                                                                rankedRanks.rank_1 = oldVal;
                                                            else if (conflictIdx === 1)
                                                                rankedRanks.rank_2 = oldVal;
                                                            else if (conflictIdx === 2)
                                                                rankedRanks.rank_3 = oldVal;
                                                            else rankedRanks.rank_4 = oldVal;
                                                        }
                                                    }
                                                    if (i === 0) rankedRanks.rank_1 = newVal!;
                                                    else if (i === 1) rankedRanks.rank_2 = newVal!;
                                                    else if (i === 2) rankedRanks.rank_3 = newVal;
                                                    else rankedRanks.rank_4 = newVal;
                                                }}
                                            >
                                                <option value="">-</option>
                                                {#each items as _, ri}
                                                    <option value={ri + 1}>{ri + 1}</option>
                                                {/each}
                                            </select>
                                        </div>
                                    {/each}
                                </div>
                            {:else if currentQuestion.type === 'rating_scale'}
                                {@const sub = currentQuestion.sub_question as RatingScaleQuestionIn}
                                <p class="mb-3 text-sm text-muted-foreground">
                                    Select your rating ({sub.min}–{sub.max}):
                                </p>
                                <div class="flex flex-wrap gap-2">
                                    {#each Array.from({ length: sub.max - sub.min + 1 }, (_, i) => sub.min + i) as val}
                                        <button
                                            onclick={() => {
                                                ratingValue = val;
                                            }}
                                            class="h-12 w-12 rounded-xl border text-sm font-medium transition-colors"
                                            class:border-primary={ratingValue === val}
                                            class:bg-primary={ratingValue === val}
                                            class:text-primary-foreground={ratingValue === val}
                                            class:border-border={ratingValue !== val}
                                            class:bg-card={ratingValue !== val}
                                            class:text-foreground={ratingValue !== val}
                                            class:hover:bg-accent={ratingValue !== val}
                                        >
                                            {val}
                                        </button>
                                    {/each}
                                </div>
                            {:else if currentQuestion.type === 'yes_no'}
                                <div class="flex gap-4">
                                    <button
                                        onclick={() => {
                                            yesNoValue = true;
                                        }}
                                        class="flex-1 rounded-xl border px-6 py-4 text-sm font-medium transition-colors {yesNoValue ===
                                        true
                                            ? 'border-green-500 bg-green-500/10 text-green-600'
                                            : 'border-border bg-card text-foreground hover:bg-accent'}"
                                    >
                                        Yes
                                    </button>
                                    <button
                                        onclick={() => {
                                            yesNoValue = false;
                                        }}
                                        class="flex-1 rounded-xl border px-6 py-4 text-sm font-medium transition-colors {yesNoValue ===
                                        false
                                            ? 'border-red-500 bg-red-500/10 text-red-600'
                                            : 'border-border bg-card text-foreground hover:bg-accent'}"
                                    >
                                        No
                                    </button>
                                </div>
                            {/if}

                            <div
                                class="sticky bottom-0 bg-background/80 backdrop-blur-sm pt-3 -mx-6 px-6 pb-6 -mb-6"
                            >
                                <button
                                    onclick={submitAnswer}
                                    class="w-full rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
                                >
                                    Submit Answer
                                </button>
                            </div>
                        </div>
                    </div>
                {:else if phase === 'answered'}
                    <div class="flex flex-col items-center py-20 text-center">
                        <div
                            class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10"
                        >
                            <svg
                                class="h-10 w-10 text-primary"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M5 13l4 4L19 7"
                                />
                            </svg>
                        </div>
                        <h2 class="mb-2 text-xl font-semibold text-(--text-heading)">
                            Answer submitted!
                        </h2>
                        <p class="text-sm text-muted-foreground">
                            Waiting for the host to move on or reveal responses…
                        </p>
                    </div>
                {:else if phase === 'revealed' && currentQuestion}
                    {@const sub = currentQuestion.sub_question}
                    <div class="space-y-6">
                        <!-- Question header -->
                        <div class="rounded-2xl border border-border bg-card p-6">
                            <span
                                class="inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
                            >
                                Question {currentQuestion.position}
                            </span>
                            <h2 class="mt-3 text-xl font-semibold text-(--text-heading)">
                                {currentQuestion.prompt}
                            </h2>
                        </div>

                        <!-- Question sub-details + aggregated results -->
                        <div class="rounded-2xl border border-border bg-card p-6">
                            {#if currentQuestion.type === 'multiple_choice'}
                                {@const mc = sub as MultipleChoiceQuestionIn}
                                {@const options = [
                                    mc.option_1,
                                    mc.option_2,
                                    mc.option_3,
                                    mc.option_4,
                                ].filter(Boolean) as string[]}
                                <div class="space-y-3">
                                    {#each options as option, i}
                                        {@const count = mcCounts[i + 1] ?? 0}
                                        {@const pct =
                                            totalResp > 0
                                                ? Math.round((count / totalResp) * 100)
                                                : 0}
                                        {@const isMine = mcSelected.includes(i + 1)}
                                        <div>
                                            <div
                                                class="flex items-center gap-3 rounded-lg border bg-background p-4 {isMine
                                                    ? 'border-primary ring-1 ring-primary/30'
                                                    : 'border-border'}"
                                            >
                                                <span
                                                    class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                                                >
                                                    {String.fromCharCode(65 + i)}
                                                </span>
                                                <span class="flex-1 text-sm">{option}</span>
                                                {#if isMine}
                                                    <span class="text-xs font-medium text-primary"
                                                        >Your answer</span
                                                    >
                                                {/if}
                                                {#if mc.allow_multiple}
                                                    <span class="text-xs text-muted-foreground"
                                                        >(multiple)</span
                                                    >
                                                {/if}
                                                {#if totalResp > 0}
                                                    <span class="tabular-nums text-sm font-semibold"
                                                        >{count}</span
                                                    >
                                                {/if}
                                            </div>
                                            {#if totalResp > 0}
                                                <div class="mt-1 h-1.5 rounded-full bg-muted">
                                                    <div
                                                        class="h-full rounded-full bg-primary transition-all duration-300"
                                                        style="width: {pct}%"
                                                    ></div>
                                                </div>
                                            {/if}
                                        </div>
                                    {/each}
                                </div>
                            {:else if currentQuestion.type === 'rating_scale'}
                                {@const rs = sub as RatingScaleQuestionIn}
                                <div class="flex flex-col items-center gap-3">
                                    <div class="flex items-center gap-3">
                                        {#each Array(rs.max - rs.min + 1) as _, i}
                                            {@const val = rs.min + i}
                                            <div
                                                class="flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium {val ===
                                                ratingValue
                                                    ? 'bg-primary text-primary-foreground ring-2 ring-primary/30'
                                                    : 'bg-muted text-foreground'}"
                                            >
                                                {val}
                                            </div>
                                        {/each}
                                    </div>
                                    <div
                                        class="flex w-full justify-between text-xs text-muted-foreground"
                                    >
                                        <span>{rs.min}</span>
                                        <span>{rs.max}</span>
                                    </div>
                                    {#if ratingValue > 0}
                                        <p class="text-xs font-medium text-muted-foreground">
                                            Your rating: <span>{ratingValue}</span>
                                        </p>
                                    {/if}
                                    {#if ratingAvg !== null}
                                        <p class="text-sm font-medium">
                                            Average: <span class="tabular-nums text-primary"
                                                >{ratingAvg}</span
                                            >
                                        </p>
                                    {/if}
                                </div>
                            {:else if currentQuestion.type === 'yes_no'}
                                <div class="flex gap-4">
                                    <div
                                        class="flex-1 rounded-xl border-2 p-6 text-center {yesNoValue ===
                                        true
                                            ? 'border-green-500 bg-green-500/10'
                                            : 'border-green-500/20 bg-green-500/5'}"
                                    >
                                        <span class="text-3xl font-bold text-green-500"
                                            >&#10003;</span
                                        >
                                        <p class="mt-1 text-sm font-medium text-foreground">Yes</p>
                                        {#if yesNoValue === true}
                                            <p class="mt-1 text-xs font-medium text-green-500">
                                                Your answer
                                            </p>
                                        {/if}
                                        {#if yesNoCounts !== null}
                                            <p class="mt-1 text-lg font-bold tabular-nums">
                                                {yesNoCounts.yes}
                                            </p>
                                        {/if}
                                    </div>
                                    <div
                                        class="flex-1 rounded-xl border-2 p-6 text-center {yesNoValue ===
                                        false
                                            ? 'border-red-500 bg-red-500/10'
                                            : 'border-red-500/20 bg-red-500/5'}"
                                    >
                                        <span class="text-3xl font-bold text-red-500">&#10007;</span
                                        >
                                        <p class="mt-1 text-sm font-medium text-foreground">No</p>
                                        {#if yesNoValue === false}
                                            <p class="mt-1 text-xs font-medium text-red-500">
                                                Your answer
                                            </p>
                                        {/if}
                                        {#if yesNoCounts !== null}
                                            <p class="mt-1 text-lg font-bold tabular-nums">
                                                {yesNoCounts.no}
                                            </p>
                                        {/if}
                                    </div>
                                </div>
                            {:else if currentQuestion.type === 'ranked_voting'}
                                {@const rv = sub as RankedVotingQuestionIn}
                                {@const items = [rv.item_1, rv.item_2, rv.item_3, rv.item_4].filter(
                                    Boolean,
                                ) as string[]}
                                <div class="space-y-2">
                                    {#each items as item, i}
                                        {@const count = rankedFirst[i] ?? 0}
                                        <div
                                            class="flex items-center gap-3 rounded-lg border border-border bg-background p-4"
                                        >
                                            <span
                                                class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                                            >
                                                {i + 1}
                                            </span>
                                            <span class="flex-1 text-sm">{item}</span>
                                            {#if totalResp > 0}
                                                <span
                                                    class="tabular-nums text-xs text-muted-foreground"
                                                    >#1 votes: {count}</span
                                                >
                                            {/if}
                                        </div>
                                    {/each}
                                </div>
                            {:else if currentQuestion.type === 'long_answer'}
                                {#if longAnswers.length > 0}
                                    <div class="max-h-64 space-y-2 overflow-y-auto">
                                        {#each longAnswers as answer}
                                            <div
                                                class="rounded-lg border p-3 text-sm {answer ===
                                                longAnswerText.trim()
                                                    ? 'border-primary bg-primary/5'
                                                    : 'border-border bg-muted/30'}"
                                            >
                                                {answer}
                                                {#if answer === longAnswerText.trim()}
                                                    <span
                                                        class="ml-2 text-xs font-medium text-primary"
                                                        >Your answer</span
                                                    >
                                                {/if}
                                            </div>
                                        {/each}
                                    </div>
                                {:else}
                                    <div
                                        class="rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center"
                                    >
                                        <p class="text-sm text-muted-foreground">
                                            No responses yet.
                                        </p>
                                    </div>
                                {/if}
                            {/if}

                            <p class="mt-4 text-center text-xs text-muted-foreground">
                                {revealedResponses.length} response{revealedResponses.length !== 1
                                    ? 's'
                                    : ''}
                            </p>
                        </div>
                    </div>
                {:else if phase === 'host_disconnected'}
                    <div class="flex flex-col items-center py-20 text-center">
                        <div
                            class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-amber-500/10"
                        >
                            <svg
                                class="h-10 w-10 text-amber-500"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M12 9v2m0 4h.01M12 3l9.66 16.5H2.34L12 3z"
                                />
                            </svg>
                        </div>
                        <h2 class="mb-2 text-xl font-semibold text-(--text-heading)">
                            Host Disconnected
                        </h2>
                        <p class="text-sm text-muted-foreground">
                            The host has temporarily left. Please wait and you'll rejoin
                            automatically when they return.
                        </p>
                    </div>
                {:else if phase === 'kicked'}
                    <div class="flex flex-col items-center py-20 text-center">
                        <div
                            class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10"
                        >
                            <UserX class="h-10 w-10 text-destructive" />
                        </div>
                        <h2 class="mb-2 text-xl font-semibold text-(--text-heading)">
                            You were removed from this meeting
                        </h2>
                        <p class="mb-6 text-sm text-muted-foreground">
                            The host has removed you from the meeting. If you believe this was a
                            mistake, please contact the meeting host.
                        </p>
                        <button
                            onclick={() => goto('/')}
                            class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            Go Home
                        </button>
                    </div>
                {:else if phase === 'ended'}
                    <div class="flex flex-col items-center py-20 text-center">
                        <div
                            class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-muted"
                        >
                            <svg
                                class="h-10 w-10 text-muted-foreground"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M5 13l4 4L19 7"
                                />
                            </svg>
                        </div>
                        <h2 class="mb-2 text-xl font-semibold text-(--text-heading)">
                            Meeting Ended
                        </h2>
                        <p class="mb-6 text-sm text-muted-foreground">
                            Thanks for participating! The meeting has now concluded.
                        </p>
                        <button
                            onclick={() => goto('/')}
                            class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            Go Home
                        </button>
                    </div>
                {/if}
            </div>
        </div>

        <!-- Sidebar: Participants + Chat (desktop only) -->
        <div class="hidden lg:flex flex-col border-l border-border">
            <div class="flex-1 min-h-0 border-b border-border">
                <HostParticipants variant="inline" {participants} />
            </div>
            <div class="flex-1 min-h-0">
                <ChatBar variant="inline" {chats} onsend={handleChatSend} />
            </div>
        </div>
    </div>

    <!-- Mobile: Participants modal -->
    <HostParticipants
        variant="modal"
        bind:open={participantsOpen}
        onclose={() => (participantsOpen = false)}
        {participants}
    />
{/if}
