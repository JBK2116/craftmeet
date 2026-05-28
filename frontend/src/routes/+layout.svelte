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
    <Navbar />
    <main class="flex-1 pb-20 md:pb-0">
        {@render children()}
    </main>
    <BottomNav />
    <Toaster
        position="top-center"
        theme="system"
        richColors
        toastOptions={{
            style: 'background: var(--card); color: var(--foreground); border: 1px solid var(--border); border-radius: var(--radius-md);',
        }}
    />
</div>
