<script lang="ts">
    import { goto } from '$app/navigation';
    import { apiFetch } from '$lib/api/auth';
    import MeetingSetup from '$lib/components/create/MeetingSetup.svelte';
    import QuestionCard from '$lib/components/create/QuestionCard.svelte';
    import { AuthError, ErrorTypes, RateLimitedError } from '$lib/types/errors';
    import type { MeetingIn, MeetingUpdate } from '$lib/types/meeting';
    import type { QuestionTypes, QuestionUpdate } from '$lib/types/question';
    import { MAX_QUESTION_CAP, MAX_TITLE_LENGTH } from '$lib/utils/constants';
    import {
        AlignStartVertical,
        ChartBar,
        ChevronDown,
        CircleAlert,
        Copy,
        ListChecks,
        Play,
        Plus,
        Star,
        ToggleLeft,
    } from '@lucide/svelte';
    import { error } from '@sveltejs/kit';
    import { untrack } from 'svelte';
    import { toast } from 'svelte-sonner';

    import type { PageData } from './$types';

    let { data }: { data: PageData } = $props();

    // question types and metadata for display
    const QUESTION_TYPES: { type: QuestionTypes; label: string; description: string }[] = [
        {
            type: 'multiple_choice',
            label: 'Multiple Choice',
            description: 'Pick from defined options',
        },
        { type: 'long_answer', label: 'Long Answer', description: 'Open text response' },
        {
            type: 'ranked_voting',
            label: 'Ranked Voting',
            description: 'Prioritize a list of items',
        },
        {
            type: 'rating_scale',
            label: 'Rating Scale',
            description: 'Numeric score within a range',
        },
        { type: 'yes_no', label: 'Yes / No', description: 'Simple binary vote' },
    ];

    // question icons for display
    const TYPE_ICONS: Record<QuestionTypes, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        yes_no: ToggleLeft,
    };

    // state
    let meeting: MeetingIn = $state(untrack(() => data.meeting as MeetingIn));
    let questions = $state<{ id: string; backendId: string | null; type: QuestionTypes }[]>(
        untrack(() =>
            [...meeting.questions]
                .sort((a, b) => a.position - b.position)
                .map((q) => ({ id: uid(), backendId: q.id, type: q.type })),
        ),
    );
    let totalQuestions = $derived(questions.length);
    let showTypeMenu = $state(false);
    let backendError = $state<string | null>(null);
    let questionCount = $derived(questions.length);
    let copyTitle = $state('');
    let copyError = $state('');
    let showCopyModal = $state(false);

    // refs used for building meeting related components
    let meetingSetupRef = $state<{ validate: () => boolean; getData: () => any } | null>(null);
    let questionRefs = $state<{ validate: () => boolean; getData: () => any }[]>([]);

    // generates a random client side id for tracking each question in the questions array
    function uid() {
        return Math.random().toString(36).slice(2, 9);
    }

    // adds a question to the questions array
    function addQuestion(type: QuestionTypes) {
        if (totalQuestions >= MAX_QUESTION_CAP) {
            toast.info(`Meetings cannot contain more than ${MAX_QUESTION_CAP} questions.`);
            return;
        }
        questions.push({ id: uid(), backendId: null, type });
        showTypeMenu = false;
    }

    // removes a question from the questions array
    function removeQuestion(id: string) {
        const idx = questions.findIndex((q) => q.id === id);
        if (idx === -1) return;
        questions.splice(idx, 1);
        questionRefs.splice(idx, 1);
    }

    // moves a question's positioning in the questions array
    function moveQuestion(index: number, direction: -1 | 1) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= questions.length) {
            return;
        }
        [questions[index], questions[newIndex]] = [questions[newIndex], questions[index]];
        [questionRefs[index], questionRefs[newIndex]] = [
            questionRefs[newIndex],
            questionRefs[index],
        ];
    }

    // Close type menu on click-outside & Escape
    $effect(() => {
        if (!showTypeMenu) {
            return;
        }
        const close = () => (showTypeMenu = false);
        const onEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') close();
        };
        const timeout = setTimeout(() => {
            document.addEventListener('click', close);
            document.addEventListener('keydown', onEscape);
        }, 0);
        return () => {
            clearTimeout(timeout);
            document.removeEventListener('click', close);
            document.removeEventListener('keydown', onEscape);
        };
    });

    async function handleUpdate() {
        // validate the meeting setup component
        const setupValid = meetingSetupRef?.validate() ?? false;
        // validate each question component individually
        const questionsValid = questionRefs.every((ref) => ref.validate());
        // ensure that both data sets are valid
        if (!setupValid || !questionsValid) {
            return;
        }
        // build the final payload
        const setupData = meetingSetupRef!.getData();
        const payload = {
            ...setupData,
            questions: questionRefs.map((ref, i) => ({
                id: questions[i].backendId,
                type: questions[i].type,
                prompt: ref.getData().prompt,
                position: i + 1,
                sub_question: ref.getData().sub_question,
            })) as QuestionUpdate[],
        } as MeetingUpdate;
        const url = `/api/v1/meetings/${meeting.id}`;
        const opts: RequestInit = {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload),
        };
        try {
            const response = await apiFetch(url, opts);
            const body = await response.json();
            if (!response.ok) {
                if (response.status === 422) {
                    backendError =
                        'The form has validation errors. Check the highlighted fields and fix them before resubmitting.';
                    return;
                }
                if (body.type === ErrorTypes.SERVER) {
                    throw new Error('Server error occurred');
                }
            }
            meeting = body as MeetingIn;
            questions = [...meeting.questions]
                .sort((a, b) => a.position - b.position)
                .map((q) => ({ id: uid(), backendId: q.id, type: q.type }));
            questionRefs = [];
            toast.success('Meeting updated successfully!', { duration: 2000 });
        } catch (err) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message);
                return;
            }
            backendError = 'An unexpected network error occurred. Please try again.';
        }
    }

    async function handleDeleteMeeting() {
        const url = `/api/v1/meetings/${meeting.id}`;
        const opts: RequestInit = { method: 'DELETE', credentials: 'include' };
        try {
            const res = await apiFetch(url, opts);
            if (!res.ok) {
                if (res.status === 404) {
                    toast.info('Meeting not found, it may have already been deleted.');
                    return;
                }
                throw new Error('Failed to delete meeting. Please try again.');
            }
            toast.success('Meeting deleted successfully');
            await goto('/dashboard');
            return;
        } catch (err: any) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message);
                return;
            }
        }
    }

    async function handleCopyMeeting() {
        if (!validateCopyTitle()) {
            return;
        }
        copyError = ''; // reset it for future use
        const payload = JSON.stringify({ title: copyTitle });
        const url = `/api/v1/meetings/${meeting.id}/copy`;
        const opts: RequestInit = {
            method: 'POST',
            credentials: 'include',
            body: payload,
            headers: { 'Content-Type': 'application/json' },
        };
        try {
            const res = await apiFetch(url, opts);
            if (!res.ok) {
                if (res.status === 404) {
                    // should never happen but good to handle it here.
                    toast.info('Meeting not found, it can no longer be copied.');
                    return;
                }
                if (res.status === 500) {
                    error(500, 'Sorry an unexpected server error occurred.');
                }
                toast.error('Sorry an unexpected server error occurred.');
                return;
            }
            showCopyModal = false;
            copyTitle = '';
            toast.success('Meeting successfully copied!');
            return;
        } catch (err: any) {
            if (err instanceof AuthError) {
                return;
            }
            if (err instanceof RateLimitedError) {
                toast.error(err.message);
                return;
            }
        }
    }

    // opens the copy meeting dialog
    function openCopyModal() {
        copyTitle = '';
        copyError = '';
        showCopyModal = true;
    }

    // close the copy dialog on Escape
    function handleCopyModalKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') showCopyModal = false;
    }

    /** Validates the copyTitle used in copy meeting requests. */
    function validateCopyTitle(): boolean {
        copyTitle = copyTitle.trim();
        if (copyTitle === '') {
            copyError = 'Title is required.';
            return false;
        }
        if (copyTitle.length > MAX_TITLE_LENGTH) {
            copyError = `Title cannot exceed ${MAX_TITLE_LENGTH} characters.`;
            return false;
        }
        if (copyTitle === meeting.title) {
            copyError = `A meeting with the title ${meeting.title} already exists.`;
            return false;
        }
        return true;
    }

    async function handleLaunchMeeting() {
        await goto(`/meetings/${meeting.id}/host`);
    }
</script>

<svelte:window onkeydown={showCopyModal ? handleCopyModalKeydown : undefined} />

{#if meeting.status === 'draft'}
    <form
        onsubmit={(e) => {
            e.preventDefault();
            handleUpdate();
        }}
        class="mx-auto max-w-2xl px-4 py-10"
    >
        <div class="mb-8 flex items-start justify-between gap-4 flex-wrap">
            <div>
                <h1
                    class="text-(--text-heading) font-bold leading-tight tracking-tight wrap-break-word"
                >
                    {meeting.title}
                </h1>
                <p class="text-meta mt-1">
                    Edit your questions, then save or launch when finished.
                </p>
            </div>
            <button
                type="button"
                onclick={handleLaunchMeeting}
                class="shrink-0 inline-flex items-center justify-center rounded-xl border border-primary p-2.5 text-primary transition-colors hover:bg-primary hover:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label="Launch meeting"
            >
                <Play class="h-5 w-5" />
            </button>
        </div>

        {#if backendError}
            <div
                class="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive flex items-start gap-3"
            >
                <CircleAlert class="h-5 w-5 shrink-0 mt-0.5" />
                <div class="flex-1 text-sm font-medium leading-relaxed">{backendError}</div>
            </div>
        {/if}

        <MeetingSetup bind:this={meetingSetupRef} initial={meeting} />

        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-(--text-subheading) font-semibold">
                Questions
                {#if questionCount > 0}
                    <span
                        class="ml-1.5 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
                    >
                        {questionCount}
                    </span>
                {/if}
            </h2>
        </div>

        {#each questions as q, i (q.id)}
            <QuestionCard
                bind:this={questionRefs[i]}
                type={q.type}
                position={i + 1}
                isFirst={i === 0}
                isLast={i === questions.length - 1}
                onremove={() => removeQuestion(q.id)}
                onmove={(direction) => moveQuestion(i, direction)}
                initial={meeting.questions.find((mq) => mq.id === q.backendId)}
            />
        {/each}

        <div class="relative mb-8">
            <button
                type="button"
                onclick={() => (showTypeMenu = !showTypeMenu)}
                class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card py-3.5 text-sm font-medium text-muted-foreground transition hover:border-primary/50 hover:bg-accent hover:text-accent-foreground"
            >
                <Plus class="h-4 w-4" />
                Add question
                <ChevronDown
                    class="h-4 w-4 transition-transform"
                    style={showTypeMenu ? 'transform: rotate(180deg)' : ''}
                />
            </button>

            {#if showTypeMenu}
                <div
                    class="absolute left-0 right-0 top-full z-20 mt-1 overflow-hidden rounded-xl border border-border bg-card shadow-overlay"
                >
                    {#each QUESTION_TYPES as qt}
                        {@const Icon = TYPE_ICONS[qt.type]}
                        <button
                            type="button"
                            onclick={() => addQuestion(qt.type)}
                            class="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-accent"
                        >
                            <div
                                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10"
                            >
                                <Icon class="h-4 w-4 text-primary" />
                            </div>
                            <div>
                                <p class="text-sm font-medium text-foreground">{qt.label}</p>
                                <p class="text-xs text-muted-foreground">{qt.description}</p>
                            </div>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>

        <div class="flex justify-between pt-4 border-t border-border">
            <button
                type="button"
                onclick={handleDeleteMeeting}
                class="inline-flex items-center justify-center rounded-xl border border-destructive/30 bg-destructive/10 px-6 py-2.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20 focus:outline-none focus:ring-2 focus:ring-ring"
            >
                Delete Meeting
            </button>
            <button
                type="button"
                onclick={openCopyModal}
                class="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-6 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
            >
                <Copy class="h-4 w-4" />
                Copy Meeting
            </button>
            <button
                type="submit"
                class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
                Save Changes
            </button>
        </div>
    </form>

    {#if showCopyModal}
        <div
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 backdrop-blur-sm"
            onclick={() => (showCopyModal = false)}
            role="presentation"
        >
            <div
                class="w-full max-w-[380px] rounded-2xl border border-border bg-card p-8 shadow-overlay"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="copy-modal-title"
                tabindex="-1"
            >
                <h2
                    id="copy-modal-title"
                    class="mb-1.5 text-center text-subheading font-semibold tracking-tight text-foreground"
                >
                    Copy Meeting
                </h2>
                <p class="mb-6 text-center text-small text-muted-foreground">
                    Choose a title for the copied meeting.
                </p>
                <input
                    id="copy-title"
                    type="text"
                    bind:value={copyTitle}
                    maxlength={MAX_TITLE_LENGTH}
                    placeholder="e.g. Q3 Team Retrospective"
                    class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    class:border-destructive={copyError !== ''}
                />
                {#if copyError}
                    <p class="mt-1 text-[var(--text-label)] text-destructive">{copyError}</p>
                {/if}
                <div class="mt-6 flex gap-3">
                    <button
                        type="button"
                        onclick={() => (showCopyModal = false)}
                        class="flex flex-1 items-center justify-center rounded-lg border border-border bg-card px-4 py-2.5 text-small font-medium text-foreground transition hover:bg-accent active:scale-[0.98]"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onclick={handleCopyMeeting}
                        class="flex flex-1 items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-small font-medium text-primary-foreground transition hover:bg-primary/90 active:scale-[0.98]"
                    >
                        Copy
                    </button>
                </div>
            </div>
        </div>
    {/if}
{:else if meeting.status === 'live'}
    <div class="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 text-center">
        <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
            <span class="relative flex h-4 w-4">
                <span
                    class="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"
                ></span>
                <span class="relative inline-flex h-4 w-4 rounded-full bg-primary"></span>
            </span>
        </div>
        <h1 class="mb-2 text-2xl font-bold text-(--text-heading)">Meeting is Live</h1>
        <p class="mb-2 text-sm text-muted-foreground">
            &ldquo;{meeting.title}&rdquo; is currently running. You are already hosting it in
            another tab.
        </p>
        <p class="mb-8 text-sm text-muted-foreground">
            Return to your host tab to continue managing the session.
        </p>
        <button
            onclick={() => goto('/dashboard')}
            class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
            Back to Dashboard
        </button>
    </div>
{:else if meeting.status === 'completed'}
    <div class="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 text-center">
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
        <h1 class="mb-2 text-2xl font-bold text-(--text-heading)">Meeting Completed</h1>
        <p class="mb-8 text-sm text-muted-foreground">
            &ldquo;{meeting.title}&rdquo; has ended. You can review the summary or return to your
            dashboard.
        </p>
        <div class="flex gap-3">
            <button
                onclick={() => goto('/dashboard')}
                class="inline-flex items-center justify-center rounded-xl border border-border bg-card px-6 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
            >
                Back to Dashboard
            </button>
            <button
                onclick={() => goto(`/meetings/${meeting.id}/summary`)}
                class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
                View Summary
            </button>
        </div>
    </div>
{/if}
