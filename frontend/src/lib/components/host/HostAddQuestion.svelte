<script lang="ts">
    import QuestionCard from '$lib/components/create/QuestionCard.svelte';
    import type { QuestionOut, QuestionTypes } from '$lib/types/question';
    import {
        AlignStartVertical,
        ChartBar,
        ListChecks,
        Plus,
        Star,
        ToggleLeft,
        X,
    } from '@lucide/svelte';

    let {
        open = $bindable(false),
        questionCount,
        onadd,
        onclose,
    }: {
        open?: boolean;
        questionCount: number;
        onadd: (question: QuestionOut) => void;
        onclose: () => void;
    } = $props();

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

    const TYPE_ICONS: Record<QuestionTypes, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        yes_no: ToggleLeft,
    };

    let selectedType = $state<QuestionTypes | null>(null);
    let questionRef = $state<{ validate: () => boolean; getData: () => QuestionOut } | null>(null);

    $effect(() => {
        if (open) {
            selectedType = null;
            questionRef = null;
        }
    });

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            onclose();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            onclose();
        }
    }

    function handleSubmit() {
        if (!questionRef) return;
        if (!questionRef.validate()) return;
        const question = questionRef.getData();
        onadd(question);
        open = false;
    }
</script>

<svelte:window onkeydown={open ? handleKeydown : undefined} />

{#if open}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
        onclick={handleBackdropClick}
        role="dialog"
        aria-modal="true"
        aria-label="Add question"
        tabindex="-1"
    >
        <!-- Modal panel -->
        <div
            class="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
        >
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-border px-5 py-4">
                <div class="flex items-center gap-2">
                    <Plus class="h-4 w-4 text-muted-foreground" />
                    <h2 class="text-sm font-semibold text-(--text-heading)">Add Question</h2>
                </div>
                <button
                    onclick={onclose}
                    class="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    aria-label="Close"
                >
                    <X class="h-4 w-4" />
                </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto px-5 py-4">
                {#if selectedType === null}
                    <p class="mb-3 text-sm text-muted-foreground">Choose a question type:</p>
                    <div class="space-y-1">
                        {#each QUESTION_TYPES as qt}
                            {@const Icon = TYPE_ICONS[qt.type]}
                            <button
                                type="button"
                                onclick={() => (selectedType = qt.type)}
                                class="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition hover:bg-accent"
                            >
                                <div
                                    class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10"
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
                {:else}
                    <QuestionCard
                        bind:this={questionRef}
                        type={selectedType}
                        position={questionCount + 1}
                        isFirst={true}
                        isLast={true}
                        onremove={() => (selectedType = null)}
                        onmove={() => {}}
                    />
                {/if}
            </div>

            <!-- Footer -->
            {#if selectedType !== null}
                <div class="flex gap-3 border-t border-border px-5 py-4">
                    <button
                        type="button"
                        onclick={() => (selectedType = null)}
                        class="flex-1 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        Back
                    </button>
                    <button
                        type="button"
                        onclick={handleSubmit}
                        class="flex-1 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        Add Question
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}
