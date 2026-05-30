<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { CircleCheck, FilePen, Video } from '@lucide/svelte';

    // table filter types
    const { tab }: { tab: 'Upcoming' | 'Drafts' | 'Completed' } = $props();

    // empty content placeholders
    const content = $derived(
        {
            Upcoming: {
                icon: Video,
                heading: 'No live meetings',
                subtext: 'Launch a draft or create a new meeting to get started.',
                cta: true,
            },
            Drafts: {
                icon: FilePen,
                heading: 'No drafts yet',
                subtext: 'Start building your first meeting.',
                cta: true,
            },
            Completed: {
                icon: CircleCheck,
                heading: 'No completed meetings',
                subtext: 'Your finished sessions will appear here.',
                cta: false,
            },
        }[tab],
    );
</script>

{#snippet body()}
    {@const Icon = content.icon}
    <div class="flex flex-col items-center gap-2 py-12 text-center">
        <Icon class="h-8 w-8 text-muted-foreground/30" />
        <span class="text-sm font-medium text-foreground">{content.heading}</span>
        <p class="max-w-xs text-xs text-muted-foreground">{content.subtext}</p>
        {#if content.cta}
            <Button href="/meetings/create" variant="outline" size="sm" class="mt-1"
                >New Meeting</Button
            >
        {/if}
    </div>
{/snippet}

{@render body()}
