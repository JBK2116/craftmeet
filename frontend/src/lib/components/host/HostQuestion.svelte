<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { MeetingIn } from '$lib/types/meeting';
    import type {
        LongAnswerQuestionIn,
        MultipleChoiceQuestionIn,
        QuestionTypes,
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
        AlignStartVertical,
        ChartBar,
        ChevronRight,
        Clock,
        Eye,
        ListChecks,
        Star,
        ToggleLeft,
        Users,
        X,
    } from '@lucide/svelte';

    let {
        meeting,
        questionIndex,
        questionElapsed,
        isLast,
        totalQuestions,
        participantCount,
        questionStates,
        responses,
        isRevealed = false,
        onreveal,
        onnext,
        onend,
    }: {
        meeting: MeetingIn;
        questionIndex: number;
        questionElapsed: number;
        questionState: 'pending' | 'open' | 'closed';
        isLast: boolean;
        totalQuestions: number;
        participantCount: number;
        questionStates: { status: 'pending' | 'open' | 'closed' }[];
        responses: ResponseOut[];
        isRevealed?: boolean;
        onreveal: () => void;
        onnext: () => void;
        onend: () => void;
    } = $props();

    let question = $derived(meeting.questions[questionIndex]);

    const TYPE_ICONS: Record<QuestionTypes, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        yes_no: ToggleLeft,
    };
    const TYPE_LABELS: Record<QuestionTypes, string> = {
        multiple_choice: 'Multiple Choice',
        long_answer: 'Long Answer',
        ranked_voting: 'Ranked Voting',
        rating_scale: 'Rating Scale',
        yes_no: 'Yes / No',
    };

    let Icon = $derived(TYPE_ICONS[question.type]);

    function formatTimer(seconds: number): string {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    let elapsedDisplay = $derived(formatTimer(questionElapsed));

    // response aggregation
    let totalResp = $derived(responses.length);

    let mcCounts = $derived.by(() => {
        if (question.type !== 'multiple_choice') return [];
        const counts: number[] = [];
        for (const r of responses as MultipleChoiceResponseOut[]) {
            for (const o of r.selected_options) {
                counts[o] = (counts[o] ?? 0) + 1;
            }
        }
        return counts;
    });

    let ratingAvg = $derived.by(() => {
        if (question.type !== 'rating_scale' || responses.length === 0) return null;
        const vals = (responses as RatingScaleResponseOut[]).map((r) => r.value);
        return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
    });

    let yesNo = $derived.by(() => {
        if (question.type !== 'yes_no') return null;
        const yes = (responses as YesNoResponseOut[]).filter((r) => r.value).length;
        return { yes, no: responses.length - yes, total: responses.length };
    });

    let rankedFirst = $derived.by(() => {
        if (question.type !== 'ranked_voting') return [];
        const counts: number[] = [0, 0, 0, 0];
        for (const r of responses as RankedVotingResponseOut[]) {
            if (r.rank_1 === 1) counts[0]++;
            if (r.rank_2 === 1) counts[1]++;
            if (r.rank_3 === 1) counts[2]++;
            if (r.rank_4 === 1) counts[3]++;
        }
        return counts;
    });

    let longAnswers = $derived.by(() => {
        if (question.type !== 'long_answer') return [];
        return (responses as LongAnswerResponseOut[]).map((r) => r.content);
    });
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <!-- Top Bar: Progress + Timer -->
    <div class="flex items-center justify-between text-sm">
        <div class="flex items-center gap-2 text-muted-foreground">
            <span class="rounded-full bg-muted px-3 py-1 text-xs font-medium">
                Question {questionIndex + 1} of {totalQuestions}
            </span>
        </div>
        <div class="flex items-center gap-3">
            <div class="flex items-center gap-1.5 text-muted-foreground">
                <Users class="h-4 w-4" />
                <span class="tabular-nums">{participantCount}</span>
            </div>
            <div class="flex items-center gap-1.5 font-mono tabular-nums text-foreground">
                <Clock class="h-4 w-4 text-muted-foreground" />
                <span>{elapsedDisplay}</span>
            </div>
        </div>
    </div>

    <!-- Question Card -->
    <div class="rounded-2xl border border-border bg-card p-6 shadow-card">
        <!-- Type Badge -->
        <div class="mb-3 flex items-center gap-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
                <Icon class="h-4 w-4 text-primary" />
            </div>
            <span class="text-xs font-medium text-muted-foreground">
                {TYPE_LABELS[question.type]}
            </span>
        </div>

        <!-- Prompt -->
        <h2 class="mb-6 text-xl font-semibold text-[var(--text-heading)] leading-relaxed">
            {question.prompt}
        </h2>

        <!-- Question-type-specific content -->
        {#if question.type === 'multiple_choice'}
            {@const sub = question.sub_question as MultipleChoiceQuestionIn}
            {@const options = [sub.option_1, sub.option_2, sub.option_3, sub.option_4].filter(
                Boolean,
            ) as string[]}
            <div class="space-y-3">
                {#each options as option, i}
                    {@const count = mcCounts[i] ?? 0}
                    {@const pct = totalResp > 0 ? Math.round((count / totalResp) * 100) : 0}
                    <div>
                        <div
                            class="flex items-center gap-3 rounded-lg border border-border bg-card p-4"
                        >
                            <span
                                class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                            >
                                {String.fromCharCode(65 + i)}
                            </span>
                            <span class="flex-1 text-sm">{option}</span>
                            {#if sub.allow_multiple}
                                <span class="text-xs text-muted-foreground">(multiple)</span>
                            {/if}
                            {#if totalResp > 0}
                                <span class="tabular-nums text-sm font-semibold">{count}</span>
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
        {:else if question.type === 'rating_scale'}
            {@const sub = question.sub_question as RatingScaleQuestionIn}
            <div class="flex flex-col items-center gap-3">
                <div class="flex items-center gap-3">
                    {#each Array(sub.max - sub.min + 1) as _, i}
                        {@const val = sub.min + i}
                        <div
                            class="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-sm font-medium text-foreground"
                        >
                            {val}
                        </div>
                    {/each}
                </div>
                <div class="flex w-full justify-between text-xs text-muted-foreground">
                    <span>{sub.min}</span>
                    <span>{sub.max}</span>
                </div>
                {#if ratingAvg !== null}
                    <p class="text-sm font-medium">
                        Average: <span class="tabular-nums text-primary">{ratingAvg}</span>
                    </p>
                {/if}
            </div>
        {:else if question.type === 'yes_no'}
            <div class="flex gap-4">
                <div
                    class="flex-1 rounded-xl border-2 border-green-500/20 bg-green-500/5 p-6 text-center"
                >
                    <span class="text-3xl font-bold text-green-500">&#10003;</span>
                    <p class="mt-1 text-sm font-medium text-foreground">Yes</p>
                    {#if yesNo !== null}
                        <p class="mt-1 text-lg font-bold tabular-nums">{yesNo.yes}</p>
                    {/if}
                </div>
                <div
                    class="flex-1 rounded-xl border-2 border-red-500/20 bg-red-500/5 p-6 text-center"
                >
                    <span class="text-3xl font-bold text-red-500">&#10007;</span>
                    <p class="mt-1 text-sm font-medium text-foreground">No</p>
                    {#if yesNo !== null}
                        <p class="mt-1 text-lg font-bold tabular-nums">{yesNo.no}</p>
                    {/if}
                </div>
            </div>
        {:else if question.type === 'ranked_voting'}
            {@const sub = question.sub_question as RankedVotingQuestionIn}
            {@const items = [sub.item_1, sub.item_2, sub.item_3, sub.item_4].filter(
                Boolean,
            ) as string[]}
            <div class="space-y-2">
                {#each items as item, i}
                    {@const count = rankedFirst[i] ?? 0}
                    <div
                        class="flex items-center gap-3 rounded-lg border border-border bg-card p-4"
                    >
                        <span
                            class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                        >
                            {i + 1}
                        </span>
                        <span class="flex-1 text-sm">{item}</span>
                        {#if totalResp > 0}
                            <span class="tabular-nums text-xs text-muted-foreground"
                                >#1 votes: {count}</span
                            >
                        {/if}
                    </div>
                {/each}
            </div>
        {:else if question.type === 'long_answer'}
            {@const sub = question.sub_question as LongAnswerQuestionIn}
            {#if longAnswers.length > 0}
                <div class="max-h-64 space-y-2 overflow-y-auto">
                    {#each longAnswers as answer}
                        <div class="rounded-lg border border-border bg-muted/30 p-3 text-sm">
                            {answer}
                        </div>
                    {/each}
                </div>
            {:else}
                <div
                    class="rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center"
                >
                    <p class="text-sm text-muted-foreground">
                        Long answer &mdash; max {sub.max_length} characters
                    </p>
                </div>
            {/if}
        {/if}
    </div>

    <!-- Controls -->
    <div class="flex items-center justify-evenly gap-3">
        <Button
            variant={isRevealed ? 'default' : 'secondary'}
            size="sm"
            onclick={onreveal}
            class="flex-1 gap-1.5 rounded-lg"
        >
            <Eye class="h-4 w-4" />
            {isRevealed ? 'Revealing…' : 'Reveal'}
        </Button>
        <Button
            variant="default"
            size="sm"
            disabled={isLast}
            onclick={onnext}
            class="flex-1 gap-1.5 rounded-lg"
        >
            <ChevronRight class="h-4 w-4" />
            Next Question
        </Button>
        <Button variant="destructive" size="sm" onclick={onend} class="flex-1 gap-1.5 rounded-lg">
            <X class="h-4 w-4" />
            End Meeting
        </Button>
    </div>

    <!-- Question Progress Dots -->
    <div class="flex items-center justify-center gap-1.5">
        {#each meeting.questions as q, i}
            {@const isCurrent = i === questionIndex}
            {@const state = questionStates[i]?.status ?? 'pending'}
            {@const dotClass = isCurrent
                ? 'w-8 bg-primary'
                : state === 'pending'
                  ? 'w-2.5 bg-muted-foreground/30'
                  : 'w-2.5 bg-muted-foreground/50'}
            <div
                class="h-2.5 rounded-full transition-all {dotClass}"
                aria-label="Question {i + 1}: {state}"
            ></div>
        {/each}
    </div>
</div>
