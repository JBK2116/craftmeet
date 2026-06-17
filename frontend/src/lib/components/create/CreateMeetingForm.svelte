<script lang="ts">
    import { apiFetch } from '$lib/api/auth';
    import type { MeetingOut } from '$lib/types/meeting';
    import type { QuestionTypes } from '$lib/types/question';
    import type { QuestionOut } from '$lib/types/question';
    import { ChevronDown, CircleAlert, Plus } from '@lucide/svelte';
    import { AlignStartVertical, ChartBar, ListChecks, Star, ToggleLeft } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';

    import MeetingSetup from './MeetingSetup.svelte';
    import QuestionCard from './QuestionCard.svelte';

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
    let questions = $state<{ id: string; type: QuestionTypes }[]>([]);
    let showTypeMenu = $state(false);
    let backendError = $state<string | null>(null); // NOTE: use this for displaying general backend errors
    let questionCount = $derived(questions.length);

    // refs used for building meeting related components
    let meetingSetupRef = $state<{ validate: () => boolean; getData: () => any } | null>(null);
    let questionRefs = $state<{ validate: () => boolean; getData: () => any }[]>([]);

    // generates a random id for each question type
    function uid() {
        return Math.random().toString(36).slice(2, 9);
    }

    // adds a new question based on the type to the questions array
    function addQuestion(type: QuestionTypes) {
        questions.push({ id: uid(), type });
        showTypeMenu = false;
    }

    // removes a question from the questions array
    function removeQuestion(id: string) {
        questions = questions.filter((q) => q.id !== id);
    }

    // moves a question up or down in the array
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

    async function handleCreate() {
        // validate the meeting setup component
        const setupValid = meetingSetupRef?.validate() ?? false;
        // valiate each question component individually
        const questionsValid = questionRefs.every((ref) => ref.validate());

        // ensure that both data sets are valid
        if (!setupValid || !questionsValid) {
            return;
        }
        const setupData = meetingSetupRef!.getData();
        // build the final payload
        const payload: MeetingOut = {
            ...setupData,
            questions: questionRefs.map(
                (ref, i) =>
                    ({
                        type: questions[i].type,
                        prompt: ref.getData().prompt,
                        position: i + 1,
                        sub_question: ref.getData().sub_question,
                    }) satisfies QuestionOut,
            ),
        };
        const url = `/api/v1/meeting/create`;
        const opts: RequestInit = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload),
        };
        try {
            const response = await apiFetch(url, opts);
            // TODO: handle the response here accordingly later
            if (!response) {
                return;
            }
            if (response.ok) {
                toast.success('Meeting created successfully.');
            }
        } catch (err) {
            backendError = 'An unexpected network error occurred. Please try again.';
            console.error(err);
        }
    }
</script>

<form
    onsubmit={(e) => {
        e.preventDefault();
        handleCreate();
    }}
    class="mx-auto max-w-2xl px-4 py-10"
>
    <div class="mb-8">
        <h1 class="text-[var(--text-heading)] font-bold leading-tight tracking-tight">
            Create Meeting
        </h1>
        <p class="text-meta mt-1">Build your question set, then launch when ready.</p>
    </div>

    {#if backendError}
        <div
            class="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive flex items-start gap-3"
        >
            <CircleAlert class="h-5 w-5 shrink-0 mt-0.5" />
            <div class="flex-1 text-sm font-medium leading-relaxed">{backendError}</div>
        </div>
    {/if}

    <MeetingSetup bind:this={meetingSetupRef} />

    <div class="mb-4 flex items-center justify-between">
        <h2 class="text-[var(--text-subheading)] font-semibold">
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

    <div class="flex justify-end pt-4 border-t border-border">
        <button
            type="submit"
            class="inline-flex items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
            Create Meeting
        </button>
    </div>
</form>
