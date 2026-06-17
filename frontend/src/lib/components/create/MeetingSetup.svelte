<script lang="ts">
    import {
        MAX_DESCRIPTION_LENGTH,
        MAX_DURATION_MINS,
        MAX_PARTICIPANT_CAP,
        MAX_TITLE_LENGTH,
    } from '$lib/utils/constants';
    import { CircleAlert, Clock, Users } from '@lucide/svelte';

    export function getData() {
        return { title, description, participant_cap, duration_minutes };
    }
    // State
    let title = $state('');
    let description = $state('');
    let participant_cap = $state(0);
    let duration_minutes = $state(0);

    // Derived
    let titleChars = $derived(title.length);
    let descChars = $derived(description.length);

    // stores the component wide errors
    const errs: Record<string, string> = $state({});

    export function validate(): boolean {
        // title validation
        if (!title.trim()) {
            errs['title'] = 'Title is required.';
        }
        if (title.trim().length > MAX_TITLE_LENGTH) {
            errs['title'] = `MAX ${MAX_TITLE_LENGTH} characters.`;
        }
        // description validation
        if (description.trim().length > MAX_DESCRIPTION_LENGTH) {
            errs['description'] = `MAX ${MAX_DESCRIPTION_LENGTH} characters.`;
        }
        // participant_cap validation
        if (participant_cap < 1 || participant_cap > MAX_PARTICIPANT_CAP) {
            errs['participant_cap'] = `Must be between 1 and ${MAX_PARTICIPANT_CAP}.`;
        }
        // duration validation
        if (duration_minutes < 1 || duration_minutes > MAX_DURATION_MINS) {
            errs['duration'] = `Duration must be between 1 and ${MAX_DURATION_MINS} mins.`;
        }
        return Object.keys(errs).length === 0;
    }
</script>

<section class="mb-4 rounded-xl border border-border bg-card p-6 shadow-card">
    <h2 class="mb-5 text-[var(--text-subheading)] font-semibold">Meeting Setup</h2>

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
            bind:value={title}
            maxlength={MAX_TITLE_LENGTH}
            placeholder="e.g. Q3 Team Retrospective"
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            class:border-destructive={errs['title']}
        />
        {#if errs['title']}
            <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                <CircleAlert class="h-3 w-3" />{errs['title']}
            </p>
        {/if}
    </div>

    <div class="mb-4">
        <div class="mb-1.5 flex items-center justify-between">
            <label for="desc">Description</label>
            <span class="text-[var(--text-label)] text-muted-foreground"
                >{descChars}/{MAX_DESCRIPTION_LENGTH}</span
            >
        </div>
        <textarea
            id="desc"
            bind:value={description}
            maxlength={MAX_DESCRIPTION_LENGTH}
            rows={3}
            placeholder="Optional context shown to participants before they join."
            class="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            class:border-destructive={errs['description']}
        ></textarea>
        {#if errs['description']}
            <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                <CircleAlert class="h-3 w-3" />{errs['description']}
            </p>
        {/if}
    </div>

    <div class="flex flex-wrap gap-4">
        <div class="flex-1 min-w-[150px]">
            <label for="cap" class="mb-1.5 flex items-center gap-1.5">
                <Users class="h-3.5 w-3.5 text-muted-foreground" />
                Participant Cap
            </label>
            <input
                id="cap"
                type="number"
                bind:value={participant_cap}
                min={1}
                max={MAX_PARTICIPANT_CAP}
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errs['participant_cap']}
            />
            {#if errs['participant_cap']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errs['participant_cap']}
                </p>
            {/if}
        </div>

        <div class="flex-1 min-w-[150px]">
            <label for="duration" class="mb-1.5 flex items-center gap-1.5">
                <Clock class="h-3.5 w-3.5 text-muted-foreground" />
                Duration (mins)
            </label>
            <input
                id="duration"
                type="number"
                bind:value={duration_minutes}
                min={1}
                max={MAX_DURATION_MINS}
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                class:border-destructive={errs['duration']}
            />
            {#if errs['duration']}
                <p class="mt-1 flex items-center gap-1 text-[var(--text-label)] text-destructive">
                    <CircleAlert class="h-3 w-3" />{errs['duration']}
                </p>
            {/if}
        </div>
    </div>
</section>
