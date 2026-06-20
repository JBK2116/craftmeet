<script lang="ts">
    import type { RatingScaleQuestionIn, RatingScaleQuestionOut } from '$lib/types/question';
    import { MAX_RATING_SCALE_VALUE, MIN_RATING_SCALE_VALUE } from '$lib/utils/constants';
    import { CircleAlert } from '@lucide/svelte';
    import { untrack } from 'svelte';

    // data sent up to the parent
    let {
        data = $bindable(),
        initial,
    }: { data: RatingScaleQuestionOut; initial?: RatingScaleQuestionIn } = $props();

    // state variables
    let min = $state(untrack(() => initial?.min ?? 0));
    let max = $state(untrack(() => initial?.max ?? 5));
    let errors = $state<Record<string, string>>({});

    // data object always reflects max, min pair
    $effect(() => {
        data = { min, max };
    });

    // ensure that the max and min are in acceptable ranges
    export function validate(): boolean {
        const errs: Record<string, string> = {};
        if (min < MIN_RATING_SCALE_VALUE || max > MAX_RATING_SCALE_VALUE) {
            errs['rating_range'] =
                `Range must be ${MIN_RATING_SCALE_VALUE}–${MAX_RATING_SCALE_VALUE}.`;
        }
        if (min >= max) {
            errs['rating_order'] = 'Min must be less than max.';
        }
        errors = errs;
        return Object.keys(errs).length === 0;
    }
</script>

<div>
    <span class="mb-2 block text-[var(--text-label)] font-medium">Scale range</span>
    <div class="flex items-center gap-3">
        <div class="flex flex-col gap-1">
            <label for="scale_min" class="text-[var(--text-label)] text-muted-foreground">Min</label
            >
            <input
                id="scale_min"
                type="number"
                bind:value={min}
                min={MIN_RATING_SCALE_VALUE}
                max={max - 1}
                class="w-20 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
        </div>
        <span class="mt-4 text-muted-foreground">→</span>
        <div class="flex flex-col gap-1">
            <label for="scale_max" class="text-[var(--text-label)] text-muted-foreground">Max</label
            >
            <input
                id="scale_max"
                type="number"
                bind:value={max}
                min={min + 1}
                max={MAX_RATING_SCALE_VALUE}
                class="w-20 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
        </div>
        <span class="mt-4 text-xs text-muted-foreground">
            ({MIN_RATING_SCALE_VALUE}–{MAX_RATING_SCALE_VALUE} allowed)
        </span>
    </div>

    {#if errors['rating_range'] || errors['rating_order']}
        <div class="mt-1.5 space-y-1">
            {#if errors['rating_range']}
                <p class="flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['rating_range']}
                </p>
            {/if}
            {#if errors['rating_order']}
                <p class="flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errors['rating_order']}
                </p>
            {/if}
        </div>
    {/if}
</div>
