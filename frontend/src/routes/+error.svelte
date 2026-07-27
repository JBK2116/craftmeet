<script lang="ts">
    import { page } from '$app/state';
</script>

<div id="error-container" class="flex flex-1 flex-col items-center justify-center text-center">
    {#if page.status === 404}
        <h1>404 Page Not Found</h1>
        <p>Sorry, the page that you are looking for does not exist.</p>
    {:else if page.status === 500}
        <h1>500 Server Error</h1>
        <p>Sorry, an unexpected server error occurred.</p>
    {:else}
        <h1>Something went wrong</h1>
        <p>{page.error?.message || 'An unexpected error occurred.'}</p>
    {/if}
</div>
