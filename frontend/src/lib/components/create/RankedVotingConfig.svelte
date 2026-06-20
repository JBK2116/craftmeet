<script lang="ts">
    import type { RankedVotingQuestionIn, RankedVotingQuestionOut } from '$lib/types/question';
    import { MAX_OPTION_LENGTH } from '$lib/utils/constants';
    import { CircleAlert, Plus, Trash2 } from '@lucide/svelte';
    import { untrack } from 'svelte';

    // data sent up to the parent component
    let {
        data = $bindable(),
        initial,
    }: { data: RankedVotingQuestionOut; initial?: RankedVotingQuestionIn } = $props();

    // state variables
    let items = $state<string[]>(
        untrack(() => {
            if (initial) {
                return [initial.item_1, initial.item_2, initial.item_3, initial.item_4].filter(
                    (i): i is string => i !== null,
                );
            }
            return ['', ''];
        }),
    );
    let errors = $state<Record<string, string>>({});
    let itemCount = $derived(items.length);

    // data is built from the existing ranked voting items
    $effect(() => {
        data = {
            item_1: items[0] ?? '',
            item_2: items[1] ?? '',
            item_3: items[2] ?? null,
            item_4: items[3] ?? null,
        };
    });

    // add an item to the items array only if space is available
    function addItem() {
        if (items.length < 4) {
            items.push('');
        }
    }

    // remove an item from the items array with mutation
    function removeItem(idx: number) {
        if (items.length > 2) {
            items.splice(idx, 1);
        }
    }

    // ensure that enough items are valid for this question to be included in the meeting
    export function validate(): boolean {
        const errs: Record<string, string> = {};
        const filled = items.filter((i) => i.trim() !== '');
        if (filled.length < 2) {
            errs['items'] = 'At least 2 items required.';
        }
        items.forEach((item, i) => {
            if (item.length > MAX_OPTION_LENGTH)
                errs[`item_${i}`] = `Max ${MAX_OPTION_LENGTH} chars.`;
        });
        errors = errs;
        return Object.keys(errs).length === 0;
    }
</script>

<div>
    <span class="mb-2 block text-[var(--text-label)] font-medium">Items to rank</span>
    <div class="space-y-2">
        {#each items as _item, i}
            <div class="flex items-center gap-2">
                <span class="w-5 shrink-0 text-center text-xs font-medium text-muted-foreground">
                    {i + 1}
                </span>
                <input
                    type="text"
                    bind:value={items[i]}
                    maxlength={MAX_OPTION_LENGTH}
                    placeholder="Item {i + 1}"
                    class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    class:border-destructive={errors[`item_${i}`]}
                />
                {#if itemCount > 2}
                    <button
                        type="button"
                        onclick={() => removeItem(i)}
                        class="rounded p-1 text-muted-foreground hover:text-destructive"
                    >
                        <Trash2 class="h-3.5 w-3.5" />
                    </button>
                {/if}
            </div>
            {#if errors[`item_${i}`]}
                <p class="ml-7 text-[var(--text-label)] text-destructive">
                    {errors[`item_${i}`]}
                </p>
            {/if}
        {/each}
    </div>

    {#if errors['items']}
        <p class="mt-1.5 flex items-center gap-1 text-[var(--text-label)] text-destructive">
            <CircleAlert class="h-3 w-3" />{errors['items']}
        </p>
    {/if}

    {#if itemCount < 4}
        <button
            type="button"
            onclick={addItem}
            class="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
            <Plus class="h-3.5 w-3.5" /> Add item
        </button>
    {:else}
        <span class="mt-3 block text-xs text-muted-foreground">Max 4 items</span>
    {/if}
</div>
