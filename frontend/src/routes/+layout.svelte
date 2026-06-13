<script lang="ts">
    import { page } from '$app/state';
    import BottomNav from '$lib/components/BottomNav.svelte';
    import Navbar from '$lib/components/Navbar.svelte';
    import { Toaster } from 'svelte-sonner';

    import './layout.css';

    const { children } = $props();

    const SITE_NAME = 'Craftmeet';
    const DEFAULT_DESCRIPTION =
        'Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces.';

    // When a route omits `meta`, build a sensible title from its final path
    // segment, e.g. "/reset-password" -> "Reset Password - Craftmeet".
    const fallbackTitle = $derived.by(() => {
        const segment = page.url.pathname.split('/').filter(Boolean).at(-1);
        if (!segment) return SITE_NAME;
        const name = segment
            .split('-')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
        return `${name} - ${SITE_NAME}`;
    });

    const meta = $derived(page.data.meta);
    const title = $derived(meta?.title ?? fallbackTitle);
    const description = $derived(meta?.description ?? DEFAULT_DESCRIPTION);
    const canonical = $derived(meta?.url);
    const ogTitle = $derived(meta?.ogTitle ?? title);
    const ogImage = $derived(meta?.ogImage ?? '/og-image.png');
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="description" content={description} />
    {#if canonical}
        <link rel="canonical" href={canonical} />
    {/if}
    <meta property="og:title" content={ogTitle} />
    <meta property="og:description" content={description} />
    {#if canonical}
        <meta property="og:url" content={canonical} />
    {/if}
    <meta property="og:type" content="website" />
    <!-- TODO: Create and place og-image.png in the static directory before launch -->
    <meta property="og:image" content={ogImage} />
</svelte:head>

<div
    class="relative flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-primary/20"
>
    <Navbar />
    <main class="flex-1 pb-20 md:pb-0">
        {@render children()}
    </main>
    <BottomNav />
    <Toaster
        position="bottom-right"
        theme="system"
        closeButton={true}
        expand={true}
        richColors={true}
        toastOptions={{
            style: 'background: var(--card); color: var(--foreground); border: 1px solid var(--border); border-radius: var(--radius-md);',
        }}
    />
</div>
