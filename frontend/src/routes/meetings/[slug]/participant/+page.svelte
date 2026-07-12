<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import type { Participant } from '$lib/types/participant';
    import type {
        LongAnswerQuestionIn,
        MultipleChoiceQuestionIn,
        QuestionIn,
        RankedVotingQuestionIn,
        RatingScaleQuestionIn,
    } from '$lib/types/question';
    import type {
        MultipleChoiceResponseOut,
        RankedVotingResponseOut,
        RatingScaleResponseOut,
        ResponseOut,
        YesNoResponseOut,
    } from '$lib/types/response';
    import {
        CloseCode,
        type CurrentQuestionPayload,
        type MeetingStartedPayload,
        MessageTypes,
        type NextQuestionPayload,
        type RevealMeetingPayload,
        type WebIn,
    } from '$lib/types/websocket';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';

    // Participant state sourced from URL query param and server messages
    let username = $state('');
    let participantId = $state<string | null>(null);

    // Meeting state
    let phase = $state<
        | 'connecting'
        | 'waiting'
        | 'question'
        | 'answered'
        | 'revealed'
        | 'host_disconnected'
        | 'ended'
    >('connecting');
    let currentQuestion = $state<QuestionIn | null>(null);
    let revealedResponses = $state<ResponseOut[]>([]);

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
        phase = 'answered';
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
                username = p.username;
                if (phase === 'connecting') phase = 'waiting';
                break;
            }
            case MessageTypes.CURRENT_QUESTION: {
                const payload = msg.payload as CurrentQuestionPayload;
                currentQuestion = payload.question;
                resetAnswerState();
                phase = 'question';
                break;
            }
            case MessageTypes.MEETING_STARTED: {
                const payload = msg.payload as MeetingStartedPayload;
                currentQuestion = payload.question;
                resetAnswerState();
                phase = 'question';
                break;
            }
            case MessageTypes.NEXT_QUESTION: {
                const payload = msg.payload as NextQuestionPayload;
                currentQuestion = payload.question;
                resetAnswerState();
                phase = 'question';
                break;
            }
            case MessageTypes.REVEAL: {
                const payload = msg.payload as RevealMeetingPayload;
                revealedResponses = payload.responses;
                phase = 'revealed';
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
                toast.info('The meeting has ended.');
                break;
            default:
                console.warn('[ws] unknown message type:', msg.type);
        }
    }

    /**
     * Handles WebSocket disconnection events.
     *
     * If the disconnection is due to a duplicate tab or invalid/expired token,
     * it displays an error toast and does not attempt to reconnect.
     * Otherwise, it shows a warning toast and schedules a reconnection attempt
     * after 3 seconds, provided the meeting has not ended.
     *
     * @param event - The CloseEvent containing the disconnection code and reason.
     */
    function handleWsDisconnect(event: CloseEvent) {
        if (destroyed) return;
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
        console.warn('[ws] participant disconnected, attempting reconnect in 3s…');
        if (phase !== 'ended') {
            toast.warning('Connection lost. Reconnecting…');
        }
        setTimeout(() => {
            if (browser && phase !== 'ended') {
                void connectWs();
            }
        }, 3000);
    }

    /**
     * Establish (or re-establish) the WebSocket connection to the meeting.
     *
     * Skips if not in a browser environment or if a connection is already open.
     * On open, sends a `participant_connected` message to register with the server.
     */
    async function connectWs() {
        if (!browser) return;
        if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

        const socket = new WebSocket(getWsUrl());
        ws = socket;

        socket.onopen = () => {
            wsConnected = true;
            // send participant_connected message with the username
            socket.send(
                JSON.stringify({ type: MessageTypes.PARTICIPANT_CONNECTED, payload: { username } }),
            );
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
            handleWsDisconnect(event);
        };

        socket.onerror = (event: Event) => {
            console.error('[ws] error:', event);
            toast.error('Connection error');
        };
    }

    onMount(() => {
        // read username from query param (set by join form)
        const nameParam = page.url.searchParams.get('name');
        if (nameParam) {
            username = nameParam;
        }

        void connectWs();
        return () => {
            destroyed = true;
            ws?.close();
            wsConnected = false;
            // clear the participant cookie when leaving
            fetch(`/api/v1/meetings/${page.params.slug}/leave`, {
                method: 'POST',
                credentials: 'include',
            }).catch(() => {});
        };
    });
</script>

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
            <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
                <span class="relative flex h-4 w-4">
                    <span
                        class="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"
                    ></span>
                    <span class="relative inline-flex h-4 w-4 rounded-full bg-primary"></span>
                </span>
            </div>
            <h1 class="mb-2 text-2xl font-bold text-[var(--text-heading)]">You're in!</h1>
            <p class="text-sm text-muted-foreground">
                Joined as <span class="font-medium text-foreground">{username}</span>. Waiting for
                the host to start the meeting…
            </p>
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
                <h2 class="mt-3 text-xl font-semibold text-[var(--text-heading)]">
                    {currentQuestion.prompt}
                </h2>
            </div>

            <!-- Answer input by type -->
            <div class="rounded-2xl border border-border bg-card p-6">
                {#if currentQuestion.type === 'multiple_choice'}
                    {@const sub = currentQuestion.sub_question as MultipleChoiceQuestionIn}
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
                                                mcSelected = mcSelected.filter((v) => v !== i + 1);
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
                    {@const sub = currentQuestion.sub_question as RankedVotingQuestionIn}
                    {@const items = [sub.item_1, sub.item_2, sub.item_3, sub.item_4].filter(
                        Boolean,
                    )}
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
                                            ].findIndex((r, idx) => idx !== i && r === newVal);
                                            if (conflictIdx !== -1) {
                                                if (conflictIdx === 0) rankedRanks.rank_1 = oldVal;
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

                <button
                    onclick={submitAnswer}
                    class="mt-6 w-full rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    Submit Answer
                </button>
            </div>
        </div>
    {:else if phase === 'answered'}
        <div class="flex flex-col items-center py-20 text-center">
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
            <h2 class="mb-2 text-xl font-semibold text-[var(--text-heading)]">Answer submitted!</h2>
            <p class="text-sm text-muted-foreground">
                Waiting for the host to move on or reveal responses…
            </p>
        </div>
    {:else if phase === 'revealed'}
        <div class="space-y-6">
            <div class="rounded-2xl border border-border bg-card p-6">
                <h2 class="text-xl font-semibold text-[var(--text-heading)]">
                    {currentQuestion?.prompt}
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                    {revealedResponses.length} response{revealedResponses.length !== 1 ? 's' : ''} revealed
                </p>
            </div>
            <div class="rounded-2xl border border-border bg-card p-6">
                {#if revealedResponses.length === 0}
                    <p class="text-sm text-muted-foreground text-center py-8">No responses yet.</p>
                {:else}
                    <div class="space-y-3">
                        {#each revealedResponses as resp}
                            <div class="rounded-xl border border-border bg-background p-4">
                                {#if resp.type === 'multiple_choice'}
                                    <p class="text-sm text-muted-foreground">
                                        Selected options: {resp.selected_options.join(', ')}
                                    </p>
                                {:else if resp.type === 'long_answer'}
                                    <p class="text-sm text-foreground">{resp.content}</p>
                                {:else if resp.type === 'ranked_voting'}
                                    <p class="text-sm text-muted-foreground">
                                        Ranks: {resp.rank_1}, {resp.rank_2}{resp.rank_3
                                            ? `, ${resp.rank_3}`
                                            : ''}{resp.rank_4 ? `, ${resp.rank_4}` : ''}
                                    </p>
                                {:else if resp.type === 'rating_scale'}
                                    <p class="text-sm text-muted-foreground">
                                        Rating: {resp.value}
                                    </p>
                                {:else if resp.type === 'yes_no'}
                                    <p class="text-sm text-foreground">
                                        {resp.value ? 'Yes' : 'No'}
                                    </p>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
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
            <h2 class="mb-2 text-xl font-semibold text-[var(--text-heading)]">Host Disconnected</h2>
            <p class="text-sm text-muted-foreground">
                The host has temporarily left. Please wait — you'll rejoin automatically when they
                return.
            </p>
        </div>
    {:else if phase === 'ended'}
        <div class="flex flex-col items-center py-20 text-center">
            <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-muted">
                <svg
                    class="h-10 w-10 text-muted-foreground"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
            </div>
            <h2 class="mb-2 text-xl font-semibold text-[var(--text-heading)]">Meeting Ended</h2>
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
