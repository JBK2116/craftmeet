<script lang="ts">
    import type { QuestionOut, QuestionTypes } from '$lib/types/question';
    import type { MultipleChoiceQuestionOut } from '$lib/types/question';
    import type { LongAnswerQuestionOut } from '$lib/types/question';
    import type { RankedVotingQuestionOut } from '$lib/types/question';
    import type { RatingScaleQuestionOut } from '$lib/types/question';
    import { MAX_PROMPT_LENGTH } from '$lib/utils/constants';
    import { CircleAlert, GripVertical, Trash2 } from '@lucide/svelte';
    import { AlignStartVertical, ChartBar, ListChecks, Star, ToggleLeft } from '@lucide/svelte';
    import { slide } from 'svelte/transition';

    import LongAnswerConfig from './LongAnswerConfig.svelte';
    import MultipleChoiceConfig from './MultipleChoiceConfig.svelte';
    import RankedVotingConfig from './RankedVotingConfig.svelte';
    import RatingScaleConfig from './RatingScaleConfig.svelte';
    import YesNoConfig from './YesNoConfig.svelte';

    let mcData: MultipleChoiceQuestionOut | null = $state(null);
    let laData: LongAnswerQuestionOut | null = $state(null);
    let rankedData: RankedVotingQuestionOut | null = $state(null);
    let ratingData: RatingScaleQuestionOut | null = $state(null);

    // Lables displayed according to selected question types
    const TYPE_LABELS: Record<QuestionTypes, string> = {
        multiple_choice: 'Multiple Choice',
        long_answer: 'Long Answer',
        ranked_voting: 'Ranked Voting',
        rating_scale: 'Rating Scale',
        yes_no: 'Yes / No',
    };

    // Icons displayed according to selected question types
    const TYPE_ICONS: Record<QuestionTypes, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        yes_no: ToggleLeft,
    };

    // Props received from parent
    interface Props {
        type: QuestionTypes;
        position: number;
        onremove: () => void;
    }

    let { type, position, onremove }: Props = $props();

    // State
    let prompt = $state('');
    let errors = $state<Record<string, string>>({});

    // Config component refs
    let configRef = $state<{ validate: () => boolean } | null>(null);

    // Derived
    let promptLen = $derived(prompt.length);
    let Icon = $derived(TYPE_ICONS[type]);

    // stores the component wide errors
    const errs: Record<string, string> = $state({});

    export function validate(): boolean {
        if (!prompt.trim()) {
            errs['prompt'] = 'Prompt is required.';
        } else if (prompt.length > MAX_PROMPT_LENGTH) {
            errs['prompt'] = `Max ${MAX_PROMPT_LENGTH} characters.`;
        }

        errors = errs;

        const configValid = configRef?.validate() ?? true;
        return Object.keys(errs).length === 0 && configValid;
    }

    export function getData(): QuestionOut {
        return {
            type,
            prompt,
            position,
            sub_question: (() => {
                switch (type) {
                    case 'multiple_choice':
                        return mcData!;
                    case 'long_answer':
                        return laData!;
                    case 'ranked_voting':
                        return rankedData!;
                    case 'rating_scale':
                        return ratingData!;
                    case 'yes_no':
                        return {};
                }
            })(),
        };
    }

    // data sent up to parent on submit
</script>

<div
    transition:slide={{ duration: 200 }}
    class="mb-3 rounded-xl border border-border bg-card shadow-card"
>
    <div class="flex items-center gap-3 border-b border-border px-4 py-3">
        <GripVertical class="h-4 w-4 shrink-0 text-muted-foreground/40" />
        <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <Icon class="h-3.5 w-3.5 text-primary" />
        </div>
        <span class="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Q{position} · {TYPE_LABELS[type]}
        </span>
        <button
            type="button"
            onclick={onremove}
            class="rounded-md p-1 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
            aria-label="Remove question"
        >
            <Trash2 class="h-4 w-4" />
        </button>
    </div>

    <div class="p-4 space-y-4">
        <div>
            <div class="mb-1.5 flex items-center justify-between">
                <label for="prompt_{position}">Prompt <span class="text-destructive">*</span></label
                >
                <span class="text-[var(--text-label)] text-muted-foreground"
                    >{promptLen}/{MAX_PROMPT_LENGTH}</span
                >
            </div>
            <input
                id="prompt_{position}"
                type="text"
                bind:value={prompt}
                maxlength={MAX_PROMPT_LENGTH}
                placeholder="Ask participants something…"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errors['prompt']}
            />
            {#if errors['prompt']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['prompt']}
                </p>
            {/if}
        </div>

        {#if type === 'multiple_choice'}
            <MultipleChoiceConfig bind:this={configRef} bind:data={mcData!} />
        {:else if type === 'long_answer'}
            <LongAnswerConfig bind:this={configRef} bind:data={laData!} />
        {:else if type === 'ranked_voting'}
            <RankedVotingConfig bind:this={configRef} bind:data={rankedData!} />
        {:else if type === 'rating_scale'}
            <RatingScaleConfig bind:this={configRef} bind:data={ratingData!} />
        {:else if type === 'yes_no'}
            <YesNoConfig bind:this={configRef} />
        {/if}
    </div>
</div>
