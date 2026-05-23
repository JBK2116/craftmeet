<script lang="ts">
    import { Toaster } from 'svelte-sonner';

    import './layout.css';

    const { children } = $props();
</script>

<Toaster />
{@render children()}
