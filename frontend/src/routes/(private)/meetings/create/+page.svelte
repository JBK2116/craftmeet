<script lang="ts">
    /**
     * BACKEND INTEGRATION TODO:
     * 1. Import API client and Meeting Service.
     * 2. Implement the POST request inside the `handleCreate` function.
     * 3. Handle the response (success redirect or backend error display).
     */
    import {
        AlignStartVertical,
        ChartBar,
        ChevronDown,
        CircleAlert,
        GripVertical,
        Lightbulb,
        ListChecks,
        Plus,
        Star,
        ToggleLeft,
        Trash2,
        Users,
    } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';
    import { slide } from 'svelte/transition';

    // Constants (mirrored from backend)
    const MAX_TITLE_LENGTH = 100;
    const MAX_DESCRIPTION_LENGTH = 500;
    const MAX_PARTICIPANT_CAP = 100;
    const MAX_PROMPT_LENGTH = 300;
    const MAX_OPTION_LENGTH = 100;
    const MAX_LONG_ANSWER_LENGTH = 2000;
    const MIN_RATING_SCALE_VALUE = 0;
    const MAX_RATING_SCALE_VALUE = 10;

    // Types
    type QuestionType =
        | 'multiple_choice'
        | 'long_answer'
        | 'ranked_voting'
        | 'rating_scale'
        | 'idea_upvote'
        | 'yes_no';

    interface MCConfig {
        options: string[]; // 2–4 options
        allow_multiple: boolean;
    }

    interface LongAnswerConfig {
        max_length: number;
    }

    interface RankedVotingConfig {
        items: string[]; // 2–4 items
    }

    interface RatingScaleConfig {
        min: number;
        max: number;
    }

    interface QuestionDraft {
        _id: string; // local only
        type: QuestionType;
        prompt: string;
        config:
            | MCConfig
            | LongAnswerConfig
            | RankedVotingConfig
            | RatingScaleConfig
            | Record<string, never>;
    }

    interface MeetingDraft {
        title: string;
        description: string;
        participant_cap: number;
        questions: QuestionDraft[];
    }

    // Question type metadata
    const QUESTION_TYPES: { type: QuestionType; label: string; description: string }[] = [
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
        { type: 'idea_upvote', label: 'Idea Upvote', description: 'Submit and vote on ideas' },
        { type: 'yes_no', label: 'Yes / No', description: 'Simple binary vote' },
    ];

    const TYPE_ICONS: Record<QuestionType, typeof ListChecks> = {
        multiple_choice: ListChecks,
        long_answer: AlignStartVertical,
        ranked_voting: ChartBar,
        rating_scale: Star,
        idea_upvote: Lightbulb,
        yes_no: ToggleLeft,
    };

    // State
    let meeting = $state<MeetingDraft>({
        title: '',
        description: '',
        participant_cap: 50,
        questions: [],
    });

    let showTypeMenu = $state(false);
    let errors = $state<Record<string, string>>({});

    // Derived
    let titleChars = $derived(meeting.title.length);
    let descChars = $derived(meeting.description.length);
    let questionCount = $derived(meeting.questions.length);

    // Close type menu on click-outside & Escape
    $effect(() => {
        if (!showTypeMenu) return;

        const close = () => {
            showTypeMenu = false;
        };
        const onEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') close();
        };

        // Use setTimeout to let the current click bubble finish before listening
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

    // Helpers
    function uid() {
        return Math.random().toString(36).slice(2, 9);
    }

    function defaultConfig(type: QuestionType) {
        switch (type) {
            case 'multiple_choice':
                return { options: ['', ''], allow_multiple: false } as MCConfig;
            case 'long_answer':
                return { max_length: MAX_LONG_ANSWER_LENGTH } as LongAnswerConfig;
            case 'ranked_voting':
                return { items: ['', ''] } as RankedVotingConfig;
            case 'rating_scale':
                return { min: 0, max: 5 } as RatingScaleConfig;
            default:
                return {} as Record<string, never>;
        }
    }

    function addQuestion(type: QuestionType) {
        meeting.questions = [
            ...meeting.questions,
            { _id: uid(), type, prompt: '', config: defaultConfig(type) },
        ];
        showTypeMenu = false;
    }

    function removeQuestion(id: string) {
        meeting.questions = meeting.questions.filter((q) => q._id !== id);
        // Clear any errors for this question
        const next: Record<string, string> = {};
        for (const [k, v] of Object.entries(errors)) {
            if (!k.startsWith(id)) next[k] = v;
        }
        errors = next;
    }

    // Option/item helpers
    function addOption(q: QuestionDraft) {
        const cfg = q.config as MCConfig;
        if (cfg.options.length < 4) cfg.options = [...cfg.options, ''];
    }

    function removeOption(q: QuestionDraft, idx: number) {
        const cfg = q.config as MCConfig;
        if (cfg.options.length > 2) cfg.options = cfg.options.filter((_, i) => i !== idx);
    }

    function addItem(q: QuestionDraft) {
        const cfg = q.config as RankedVotingConfig;
        if (cfg.items.length < 4) cfg.items = [...cfg.items, ''];
    }

    function removeItem(q: QuestionDraft, idx: number) {
        const cfg = q.config as RankedVotingConfig;
        if (cfg.items.length > 2) cfg.items = cfg.items.filter((_, i) => i !== idx);
    }

    // Reset form to initial state
    function resetForm() {
        meeting = { title: '', description: '', participant_cap: 50, questions: [] };
        errors = {};
    }

    // Validation
    function validate(): boolean {
        const errs: Record<string, string> = {};

        if (!meeting.title.trim()) errs['title'] = 'Title is required.';
        else if (meeting.title.length > MAX_TITLE_LENGTH)
            errs['title'] = `Max ${MAX_TITLE_LENGTH} characters.`;

        if (meeting.description.length > MAX_DESCRIPTION_LENGTH)
            errs['description'] = `Max ${MAX_DESCRIPTION_LENGTH} characters.`;

        if (meeting.participant_cap < 1 || meeting.participant_cap > MAX_PARTICIPANT_CAP)
            errs['participant_cap'] = `Must be between 1 and ${MAX_PARTICIPANT_CAP}.`;

        if (meeting.questions.length === 0) errs['questions'] = 'Add at least one question.';

        for (const q of meeting.questions) {
            if (!q.prompt.trim()) errs[`${q._id}_prompt`] = 'Prompt is required.';
            else if (q.prompt.length > MAX_PROMPT_LENGTH)
                errs[`${q._id}_prompt`] = `Max ${MAX_PROMPT_LENGTH} characters.`;

            if (q.type === 'multiple_choice') {
                const cfg = q.config as MCConfig;
                const filled = cfg.options.filter((o) => o.trim());
                if (filled.length < 2) errs[`${q._id}_options`] = 'At least 2 options required.';
                cfg.options.forEach((o, i) => {
                    if (o.length > MAX_OPTION_LENGTH)
                        errs[`${q._id}_opt_${i}`] = `Max ${MAX_OPTION_LENGTH} chars.`;
                });
            }

            if (q.type === 'ranked_voting') {
                const cfg = q.config as RankedVotingConfig;
                const filled = cfg.items.filter((i) => i.trim());
                if (filled.length < 2) errs[`${q._id}_items`] = 'At least 2 items required.';
                cfg.items.forEach((item, i) => {
                    if (item.length > MAX_OPTION_LENGTH)
                        errs[`${q._id}_item_${i}`] = `Max ${MAX_OPTION_LENGTH} chars.`;
                });
            }

            if (q.type === 'rating_scale') {
                const cfg = q.config as RatingScaleConfig;
                if (cfg.min < MIN_RATING_SCALE_VALUE || cfg.max > MAX_RATING_SCALE_VALUE)
                    errs[`${q._id}_rating_range`] =
                        `Range must be ${MIN_RATING_SCALE_VALUE}–${MAX_RATING_SCALE_VALUE}.`;
                if (cfg.min >= cfg.max)
                    errs[`${q._id}_rating_order`] = 'Min must be less than max.';
            }
        }
        errors = errs;
        return Object.keys(errs).length === 0;
    }

    // Submit
    function handleCreate() {
        if (!validate()) return;

        // Build final payload (shape matches backend schema)
        const payload = {
            title: meeting.title.trim(),
            description: meeting.description.trim() || null,
            participant_cap: meeting.participant_cap,
            questions: meeting.questions.map((q, idx) => ({
                type: q.type,
                prompt: q.prompt.trim(),
                position: idx + 1,
                ...q.config,
            })),
        };
        // TODO: At this section, integrate this with the backend
        toast.success('Meeting payload created. Check the console for more details', {
            duration: Infinity,
        });
        console.log('[handleCreate] payload:', JSON.stringify(payload, null, 2));
    }
</script>

<!-- Builder -->
<form
    onsubmit={(e) => {
        e.preventDefault();
        handleCreate();
    }}
    class="mx-auto max-w-2xl px-4 py-10"
>
    <!-- Page header -->
    <div class="mb-8">
        <h1 class="text-[var(--text-heading)] font-bold leading-tight tracking-tight">
            Create Meeting
        </h1>
        <p class="text-meta mt-1">Build your question set, then launch when ready.</p>
    </div>

    <!-- Meeting Setup Card -->
    <section class="mb-4 rounded-xl border border-border bg-card p-6 shadow-card">
        <h2 class="mb-5 text-[var(--text-subheading)] font-semibold">Meeting Setup</h2>

        <!-- Title -->
        <div class="mb-4">
            <div class="mb-1.5 flex items-center justify-between">
                <label for="title">Title <span class="text-destructive">*</span></label>
                <span class="text-[var(--text-label)] text-muted-foreground"
                    >{titleChars}/{MAX_TITLE_LENGTH}</span
                >
            </div>
            <input
                id="title"
                type="text"
                bind:value={meeting.title}
                maxlength={MAX_TITLE_LENGTH}
                placeholder="e.g. Q3 Team Retrospective"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errors['title']}
            />
            {#if errors['title']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['title']}
                </p>
            {/if}
        </div>

        <!-- Description -->
        <div class="mb-4">
            <div class="mb-1.5 flex items-center justify-between">
                <label for="desc">Description</label>
                <span class="text-[var(--text-label)] text-muted-foreground"
                    >{descChars}/{MAX_DESCRIPTION_LENGTH}</span
                >
            </div>
            <textarea
                id="desc"
                bind:value={meeting.description}
                maxlength={MAX_DESCRIPTION_LENGTH}
                rows={3}
                placeholder="Optional context shown to participants before they join."
                class="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errors['description']}
            ></textarea>
            {#if errors['description']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['description']}
                </p>
            {/if}
        </div>

        <!-- Participant Cap -->
        <div>
            <label for="cap" class="mb-1.5 flex items-center gap-1.5">
                <Users class="h-3.5 w-3.5 text-muted-foreground" />
                Participant Cap
            </label>
            <input
                id="cap"
                type="number"
                bind:value={meeting.participant_cap}
                min={1}
                max={MAX_PARTICIPANT_CAP}
                class="w-32 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errors['participant_cap']}
            />
            {#if errors['participant_cap']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['participant_cap']}
                </p>
            {/if}
        </div>
    </section>

    <!-- Questions -->
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

    {#if errors['questions']}
        <p class="mb-3 flex items-center gap-1.5 text-[var(--text-small)] text-destructive">
            <CircleAlert class="h-4 w-4" />{errors['questions']}
        </p>
    {/if}

    <!-- Question Cards -->
    {#each meeting.questions as q, idx (q._id)}
        {@const Icon = TYPE_ICONS[q.type]}
        <div
            transition:slide={{ duration: 200 }}
            class="mb-3 rounded-xl border border-border bg-card shadow-card"
        >
            <!-- Card Header -->
            <div class="flex items-center gap-3 border-b border-border px-4 py-3">
                <GripVertical class="h-4 w-4 shrink-0 text-muted-foreground/40" />
                <div
                    class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10"
                >
                    <Icon class="h-3.5 w-3.5 text-primary" />
                </div>
                <span
                    class="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                    Q{idx + 1} · {QUESTION_TYPES.find((t) => t.type === q.type)?.label}
                </span>
                <button
                    onclick={() => removeQuestion(q._id)}
                    class="rounded-md p-1 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                    aria-label="Remove question"
                >
                    <Trash2 class="h-4 w-4" />
                </button>
            </div>

            <div class="p-4 space-y-4">
                <!-- Prompt -->
                <div>
                    <div class="mb-1.5 flex items-center justify-between">
                        <label for="prompt_{q._id}"
                            >Prompt <span class="text-destructive">*</span></label
                        >
                        <span class="text-[var(--text-label)] text-muted-foreground"
                            >{q.prompt.length}/{MAX_PROMPT_LENGTH}</span
                        >
                    </div>
                    <input
                        id="prompt_{q._id}"
                        type="text"
                        bind:value={q.prompt}
                        maxlength={MAX_PROMPT_LENGTH}
                        placeholder="Ask participants something…"
                        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        class:border-destructive={errors[`${q._id}_prompt`]}
                    />
                    {#if errors[`${q._id}_prompt`]}
                        <p
                            class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive"
                        >
                            <CircleAlert class="h-3 w-3" />{errors[`${q._id}_prompt`]}
                        </p>
                    {/if}
                </div>

                <!-- Type-specific config -->

                <!-- MULTIPLE CHOICE -->
                {#if q.type === 'multiple_choice'}
                    {@const cfg = q.config as MCConfig}
                    <div>
                        <span class="mb-2 block text-[var(--text-label)] font-medium">Options</span>
                        <div class="space-y-2">
                            {#each cfg.options as _option, i}
                                <div class="flex items-center gap-2">
                                    <span
                                        class="w-5 shrink-0 text-center text-xs font-medium text-muted-foreground"
                                        >{i + 1}</span
                                    >
                                    <input
                                        type="text"
                                        bind:value={cfg.options[i]}
                                        maxlength={MAX_OPTION_LENGTH}
                                        placeholder="Option {i + 1}"
                                        class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                                        class:border-destructive={errors[`${q._id}_opt_${i}`]}
                                    />
                                    {#if cfg.options.length > 2}
                                        <button
                                            onclick={() => removeOption(q, i)}
                                            class="rounded p-1 text-muted-foreground hover:text-destructive"
                                        >
                                            <Trash2 class="h-3.5 w-3.5" />
                                        </button>
                                    {/if}
                                </div>
                                {#if errors[`${q._id}_opt_${i}`]}
                                    <p class="ml-7 text-[var(--text-label)] text-destructive">
                                        {errors[`${q._id}_opt_${i}`]}
                                    </p>
                                {/if}
                            {/each}
                        </div>
                        {#if errors[`${q._id}_options`]}
                            <p
                                class="mt-1.5 flex items-center gap-1 text-[var(--text-label)] text-destructive"
                            >
                                <CircleAlert class="h-3 w-3" />{errors[`${q._id}_options`]}
                            </p>
                        {/if}
                        <div class="mt-3 flex items-center justify-between">
                            {#if cfg.options.length < 4}
                                <button
                                    onclick={() => addOption(q)}
                                    class="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                                >
                                    <Plus class="h-3.5 w-3.5" /> Add option
                                </button>
                            {:else}
                                <span class="text-xs text-muted-foreground">Max 4 options</span>
                            {/if}
                            <label
                                class="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground"
                            >
                                <input
                                    type="checkbox"
                                    bind:checked={cfg.allow_multiple}
                                    class="rounded border-input"
                                />
                                Allow multiple selections
                            </label>
                        </div>
                    </div>
                {/if}

                <!-- LONG ANSWER -->
                {#if q.type === 'long_answer'}
                    {@const cfg = q.config as LongAnswerConfig}
                    <div>
                        <label for="{q._id}_max_length" class="mb-1.5 block"
                            >Max response length</label
                        >
                        <div class="flex items-center gap-3">
                            <input
                                id="{q._id}_max_length"
                                type="number"
                                bind:value={cfg.max_length}
                                min={50}
                                max={MAX_LONG_ANSWER_LENGTH}
                                class="w-28 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                            <span class="text-xs text-muted-foreground"
                                >characters (max {MAX_LONG_ANSWER_LENGTH})</span
                            >
                        </div>
                    </div>
                {/if}

                <!-- RANKED VOTING -->
                {#if q.type === 'ranked_voting'}
                    {@const cfg = q.config as RankedVotingConfig}
                    <div>
                        <span class="mb-2 block text-[var(--text-label)] font-medium"
                            >Items to rank</span
                        >
                        <div class="space-y-2">
                            {#each cfg.items as _item, i}
                                <div class="flex items-center gap-2">
                                    <span
                                        class="w-5 shrink-0 text-center text-xs font-medium text-muted-foreground"
                                        >{i + 1}</span
                                    >
                                    <input
                                        type="text"
                                        bind:value={cfg.items[i]}
                                        maxlength={MAX_OPTION_LENGTH}
                                        placeholder="Item {i + 1}"
                                        class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                                        class:border-destructive={errors[`${q._id}_item_${i}`]}
                                    />
                                    {#if cfg.items.length > 2}
                                        <button
                                            onclick={() => removeItem(q, i)}
                                            class="rounded p-1 text-muted-foreground hover:text-destructive"
                                        >
                                            <Trash2 class="h-3.5 w-3.5" />
                                        </button>
                                    {/if}
                                </div>
                                {#if errors[`${q._id}_item_${i}`]}
                                    <p class="ml-7 text-[var(--text-label)] text-destructive">
                                        {errors[`${q._id}_item_${i}`]}
                                    </p>
                                {/if}
                            {/each}
                        </div>
                        {#if errors[`${q._id}_items`]}
                            <p
                                class="mt-1.5 flex items-center gap-1 text-[var(--text-label)] text-destructive"
                            >
                                <CircleAlert class="h-3 w-3" />{errors[`${q._id}_items`]}
                            </p>
                        {/if}
                        {#if cfg.items.length < 4}
                            <button
                                onclick={() => addItem(q)}
                                class="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                            >
                                <Plus class="h-3.5 w-3.5" /> Add item
                            </button>
                        {:else}
                            <span class="mt-3 block text-xs text-muted-foreground">Max 4 items</span
                            >
                        {/if}
                    </div>
                {/if}

                <!-- RATING SCALE -->
                {#if q.type === 'rating_scale'}
                    {@const cfg = q.config as RatingScaleConfig}
                    <div>
                        <span class="mb-2 block text-[var(--text-label)] font-medium"
                            >Scale range</span
                        >
                        <div class="flex items-center gap-3">
                            <div class="flex flex-col gap-1">
                                <label
                                    for="{q._id}_scale_min"
                                    class="text-[var(--text-label)] text-muted-foreground"
                                    >Min</label
                                >
                                <input
                                    id="{q._id}_scale_min"
                                    type="number"
                                    bind:value={cfg.min}
                                    min={MIN_RATING_SCALE_VALUE}
                                    max={cfg.max - 1}
                                    class="w-20 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                                />
                            </div>
                            <span class="mt-4 text-muted-foreground">→</span>
                            <div class="flex flex-col gap-1">
                                <label
                                    for="{q._id}_scale_max"
                                    class="text-[var(--text-label)] text-muted-foreground"
                                    >Max</label
                                >
                                <input
                                    id="{q._id}_scale_max"
                                    type="number"
                                    bind:value={cfg.max}
                                    min={cfg.min + 1}
                                    max={MAX_RATING_SCALE_VALUE}
                                    class="w-20 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                                />
                            </div>
                            <span class="mt-4 text-xs text-muted-foreground"
                                >({MIN_RATING_SCALE_VALUE}–{MAX_RATING_SCALE_VALUE} allowed)</span
                            >
                        </div>
                        {#if errors[`${q._id}_rating_range`] || errors[`${q._id}_rating_order`]}
                            <div class="mt-1.5 space-y-1">
                                {#if errors[`${q._id}_rating_range`]}
                                    <p
                                        class="flex items-center gap-1 text-[var(--text-label)] text-destructive"
                                    >
                                        <CircleAlert class="h-3 w-3" />{errors[
                                            `${q._id}_rating_range`
                                        ]}
                                    </p>
                                {/if}
                                {#if errors[`${q._id}_rating_order`]}
                                    <p
                                        class="flex items-center gap-1 text-[var(--text-label)] text-destructive"
                                    >
                                        <CircleAlert class="h-3 w-3" />{errors[
                                            `${q._id}_rating_order`
                                        ]}
                                    </p>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- IDEA UPVOTE -->
                {#if q.type === 'idea_upvote'}
                    <p class="rounded-lg bg-muted px-3 py-2.5 text-xs text-muted-foreground">
                        Participants submit their own ideas. Others can upvote them in real-time. No
                        extra config needed.
                    </p>
                {/if}

                <!-- YES / NO -->
                {#if q.type === 'yes_no'}
                    <p class="rounded-lg bg-muted px-3 py-2.5 text-xs text-muted-foreground">
                        Participants vote Yes or No. Results shown as a live split. No extra config
                        needed.
                    </p>
                {/if}
            </div>
        </div>
    {/each}

    <!-- Add Question -->
    <div class="relative mb-8">
        <button
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

    <!-- Submit -->
    <button
        type="submit"
        class="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow-cta transition hover:bg-primary/90 active:scale-[0.99]"
    >
        Create Meeting
    </button>

    {#if Object.keys(errors).length > 0}
        <p class="mt-3 flex items-center justify-center gap-1.5 text-sm text-destructive">
            <CircleAlert class="h-4 w-4" />
            Fix the errors above before continuing.
        </p>
    {/if}
</form>
