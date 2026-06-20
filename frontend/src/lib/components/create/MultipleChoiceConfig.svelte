<script lang="ts">
    import type { MultipleChoiceQuestionIn, MultipleChoiceQuestionOut } from '$lib/types/question';
    import { MAX_OPTION_LENGTH } from '$lib/utils/constants';
    import { CircleAlert, Plus, Trash2 } from '@lucide/svelte';
    import { untrack } from 'svelte';

    let {
        data = $bindable(),
        initial,
    }: { data: MultipleChoiceQuestionOut; initial?: MultipleChoiceQuestionIn } = $props();

    // state variables
    let options = $state<string[]>(
        untrack(() => {
            if (initial) {
                return [
                    initial.option_1,
                    initial.option_2,
                    initial.option_3,
                    initial.option_4,
                ].filter((o): o is string => o !== null);
            }
            return ['', ''];
        }),
    );
    let allow_multiple = $state(untrack(() => initial?.allow_multiple ?? false));
    let errors = $state<Record<string, string>>({});
    let optionCount = $derived(options.length);

    $effect(() => {
        data = {
            option_1: options[0] ?? '',
            option_2: options[1] ?? '',
            option_3: options[2] ?? null,
            option_4: options[3] ?? null,
            allow_multiple,
        };
    });

    function addOption() {
        if (options.length < 4) {
            options.push('');
        }
    }

    function removeOption(idx: number) {
        if (options.length > 2) {
            options.splice(idx, 1);
        }
    }

    export function validate(): boolean {
        const errs: Record<string, string> = {};
        const filled = options.filter((o) => o.trim());
        if (filled.length < 2) {
            errs['options'] = 'At least 2 options required.';
        }
        options.forEach((o, i) => {
            if (o.length > MAX_OPTION_LENGTH) {
                errs[`opt_${i}`] = `Max ${MAX_OPTION_LENGTH} chars.`;
            }
        });
        errors = errs;
        return Object.keys(errs).length === 0;
    }
</script>

<div>
    <span class="mb-2 block text-[var(--text-label)] font-medium">Options</span>
    <div class="space-y-2">
        {#each options as _option, i}
            <div class="flex items-center gap-2">
                <span class="w-5 shrink-0 text-center text-xs font-medium text-muted-foreground">
                    {i + 1}
                </span>
                <input
                    type="text"
                    bind:value={options[i]}
                    maxlength={MAX_OPTION_LENGTH}
                    placeholder="Option {i + 1}"
                    class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    class:border-destructive={errors[`opt_${i}`]}
                />
                {#if optionCount > 2}
                    <button
                        type="button"
                        onclick={() => removeOption(i)}
                        class="rounded p-1 text-muted-foreground hover:text-destructive"
                    >
                        <Trash2 class="h-3.5 w-3.5" />
                    </button>
                {/if}
            </div>
            {#if errors[`opt_${i}`]}
                <p class="ml-7 text-[var(--text-label)] text-destructive">
                    {errors[`opt_${i}`]}
                </p>
            {/if}
        {/each}
    </div>

    {#if errors['options']}
        <p class="mt-1.5 flex items-center gap-1 text-[var(--text-label)] text-destructive">
            <CircleAlert class="h-3 w-3" />{errors['options']}
        </p>
    {/if}

    <div class="mt-3 flex items-center justify-between">
        {#if optionCount < 4}
            <button
                type="button"
                onclick={addOption}
                class="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
                <Plus class="h-3.5 w-3.5" /> Add option
            </button>
        {:else}
            <span class="text-xs text-muted-foreground">Max 4 options</span>
        {/if}
        <label class="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
            <input type="checkbox" bind:checked={allow_multiple} class="rounded border-input" />
            Allow multiple selections
        </label>
    </div>
</div>
