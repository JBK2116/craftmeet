<script lang="ts">
    import BottomNav from '$lib/components/BottomNav.svelte';
    import Navbar from '$lib/components/Navbar.svelte';
    import { Toaster } from 'svelte-sonner';

    import './layout.css';

    const { children } = $props();
</script>

<div
    class="relative flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-primary/20"
>
    <div
        class="sticky top-0 z-40 w-full border-b border-border bg-background/80 backdrop-blur-lg hidden md:block"
    >
        <Navbar />
    </div>

    <main class="flex-1 pb-20 md:pb-0">
        {@render children()}
    </main>

    <div
        class="fixed bottom-0 left-0 right-0 z-40 block border-t border-border bg-background/80 backdrop-blur-lg md:hidden"
    >
        <BottomNav />
    </div>

    <Toaster
        position="top-center"
        theme="system"
        richColors
        toastOptions={{
            style: 'background: var(--card); color: var(--foreground); border: 1px solid var(--border); border-radius: var(--radius-md);',
        }}
    />
</div>
