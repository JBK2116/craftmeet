<script lang="ts">
    import type { LongAnswerQuestionOut } from '$lib/types/question';
    import { MAX_LONG_ANSWER_LENGTH } from '$lib/utils/constants';
    
    // data sent up to the parent
    let { data = $bindable() }: { data: LongAnswerQuestionOut } = $props();

    // state
    let max_length = $state(MAX_LONG_ANSWER_LENGTH);

    $effect(() => {
        data = { max_length };
    });

    export function validate(): boolean {
        return max_length >= 50 && max_length <= MAX_LONG_ANSWER_LENGTH;
    }
</script>

<div>
    <label for="max_length" class="mb-1.5 block">Max response length</label>
    <div class="flex items-center gap-3">
        <input
            id="max_length"
            type="number"
            bind:value={max_length}
            min={50}
            max={MAX_LONG_ANSWER_LENGTH}
            class="w-28 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <span class="text-xs text-muted-foreground">characters (max {MAX_LONG_ANSWER_LENGTH})</span>
    </div>
</div>
