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
    <div class="flex flex-col items-center gap-3 py-16 text-center">
        <Icon class="h-10 w-10 text-muted-foreground/40" />
        <span class="font-medium text-foreground">{content.heading}</span>
        <p class="text-meta max-w-xs">{content.subtext}</p>
        {#if content.cta}
            <Button href="/meetings/create" class="mt-1">New Meeting</Button>
        {/if}
    </div>
{/snippet}

{@render body()}
