<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { onMount } from 'svelte';

    // Extract verification token from the URL
    // e.g. GET /verify-email?token=<jwt>
    let verifyToken = $derived(page.url.searchParams.get('token') ?? '');

    // verification status text shown beneath the spinner
    let statusText = $state('Verifying email');

    const successParams = new URLSearchParams({ verified_email: 'true' });
    const failedParams = new URLSearchParams({ verified_email: 'false' });
    // verify token functionality
    async function handleVerify(): Promise<void> {
        try {
            // URL Params sent to redirect request
            if (!verifyToken) {
                await goto(`/login?${failedParams.toString()}`);
                return;
            }
            const url = `/api/v1/auth/verify-email`;
            const body = { token: verifyToken };
            const response = await fetch(url, {
                method: 'POST',
                body: JSON.stringify(body),
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                await goto(`/login?${failedParams.toString()}`);
                return;
            }
            await goto(`/login?${successParams.toString()}`);
        } catch (err: any) {
            // for any random error such as this, simply redirect the user to login so they know that they were unable to verify their email
            // errors like this are rare, so the user will simply have to request another token which will be handled by the backend
            await goto(`/login?${failedParams.toString()}`);
        }
    }

    onMount(() => {
        handleVerify();
    });
</script>

<svelte:head>
    <title>Verify Email - Craftmeet</title>
    <meta name="description" content="Confirming your Craftmeet email address." />
    <link rel="canonical" href="https://craftmeet.com/verify-email" />
    <meta property="og:title" content="Craftmeet - Verify Email" />
    <meta property="og:description" content="Confirming your Craftmeet email address." />
    <meta property="og:url" content="https://craftmeet.com/verify-email" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/og-image.png" />
</svelte:head>

<div
    class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm"
>
    <div class="flex flex-col items-center gap-4">
        <div class="h-8 w-8 rounded-full border-2 border-muted border-t-primary animate-spin"></div>
        <p class="text-sm text-muted-foreground">{statusText}</p>
    </div>
</div>
