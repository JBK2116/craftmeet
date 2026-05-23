<script lang="ts">
    import BottomNav from '$lib/components/BottomNav.svelte';
    import Navbar from '$lib/components/Navbar.svelte';
    import { Toaster } from 'svelte-sonner';

    import './layout.css';

    const { children } = $props();
</script>

<Navbar />
<BottomNav />
<Toaster />
{@render children()}
