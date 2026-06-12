<script lang="ts">
    import EmailModal from '$lib/components/EmailModal.svelte';
    import { ErrorTypes } from '$lib/types/errors';
    import { toast } from 'svelte-sonner';

    let isSubmitting = $state(false);
    let showSuccessModal = $state(false);

    let email = $state('');
    let emailError = $state('');

    function validateEmail(): boolean {
        const value = email.trim();
        if (value.length < 3 || value.length > 254) {
            emailError = 'Email address length is invalid';
            return false;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            emailError = 'Please enter a valid email address';
            return false;
        }
        if (value.includes('..')) {
            emailError = 'Email cannot contain consecutive periods';
            return false;
        }
        const [local, domain] = value.split('@');
        if (local.length > 64) {
            emailError = 'Email username portion is too long';
            return false;
        }
        const labels = domain.split('.');
        for (const label of labels) {
            if (label.startsWith('-') || label.endsWith('-')) {
                emailError = 'Email domain format is invalid';
                return false;
            }
        }
        emailError = '';
        return true;
    }
    const url = `/api/v1/auth/forgot-password`;
    async function handleSubmit(): Promise<void> {
        if (!validateEmail()) return;
        isSubmitting = true;
        try {
            const body = { email: email };
            const headers = { 'Content-Type': 'application/json' };
            const response = await fetch(url, {
                method: 'POST',
                body: JSON.stringify(body),
                headers,
            });
            if (!response.ok) {
                const body = await response.json();
                if (response.status === 422) {
                    emailError = 'Please enter a valid email address';
                    return;
                }
                switch (body.type) {
                    case ErrorTypes.EMAIL:
                        emailError = body.message;
                        return;
                    case ErrorTypes.SERVER:
                        toast.error(
                            'We could not send your reset link. There was a temporary problem with our service. Please try again in a few minutes.',
                            { duration: Infinity },
                        );
                        return;
                }
            }
            await new Promise((resolve) => setTimeout(resolve, 2000));
            showSuccessModal = true;
        } catch (err: any) {
            toast.error(
                'We could not send your reset link. There was a temporary problem with our service. Please try again in a few minutes.',
                { duration: Infinity },
            );
        } finally {
            isSubmitting = false;
        }
    }
</script>

<svelte:head>
    <title>Forgot Password - Craftmeet</title>
    <meta name="description" content="Reset your Craftmeet account password." />
    <link rel="canonical" href="https://craftmeet.com/forgot-password" />
    <meta property="og:title" content="Craftmeet - Forgot Password" />
    <meta property="og:description" content="Reset your Craftmeet account password." />
    <meta property="og:url" content="https://craftmeet.com/forgot-password" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/og-image.png" />
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-4 py-16">
    <div class="w-full max-w-[420px] space-y-3">
        <div class="rounded-2xl border border-border bg-card px-8 py-9">
            <h1 class="mb-1 text-center text-heading font-semibold tracking-tight text-foreground">
                Forgot your password?
            </h1>
            <p class="mb-7 text-center text-small text-muted-foreground">
                Enter your email and we'll send you a reset link.
            </p>

            <div class="space-y-4">
                <div class="space-y-1.5">
                    <label for="email" class="block text-small font-medium text-muted-foreground">
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        onblur={validateEmail}
                        placeholder="you@example.com"
                        disabled={isSubmitting}
                        class="w-full rounded-lg border px-3.5 py-2.5 text-small text-foreground placeholder:text-muted-foreground outline-none transition bg-background
                            focus:ring-2 focus:ring-primary/20 focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-40
                            {emailError
                            ? 'border-destructive bg-destructive/10 focus:ring-destructive/20 focus:border-destructive'
                            : 'border-border'}"
                    />
                    {#if emailError}
                        <p class="flex items-center gap-1.5 text-label text-destructive">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                class="h-3.5 w-3.5 shrink-0"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                            {emailError}
                        </p>
                    {/if}
                </div>

                <button
                    onclick={handleSubmit}
                    disabled={isSubmitting}
                    class="mt-1 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-small font-medium text-primary-foreground transition
                        hover:bg-primary/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {#if isSubmitting}
                        <svg
                            class="h-4 w-4 animate-spin"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                            />
                            <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                            />
                        </svg>
                        Sending…
                    {:else}
                        Send reset link
                    {/if}
                </button>
            </div>
        </div>

        <div
            class="rounded-xl border border-border bg-card px-8 py-4 text-center text-small text-muted-foreground"
        >
            Remember your password?
            <a
                href="/login"
                class="ml-1 font-medium text-foreground underline-offset-2 hover:underline hover:text-muted-foreground transition-colors"
            >
                Sign in
            </a>
        </div>

        <p class="text-center text-label text-muted-foreground">
            <a href="/privacy" class="hover:text-foreground transition-colors">Privacy Policy</a>
            <span class="mx-1.5">·</span>
            <a href="/terms" class="hover:text-foreground transition-colors">Terms of Service</a>
        </p>
    </div>
</main>

<EmailModal
    bind:open={showSuccessModal}
    title="Check your inbox"
    message={`If ${email} is associated with an account, you'll receive a reset link shortly. Be sure to check your spam folder.`}
/>
