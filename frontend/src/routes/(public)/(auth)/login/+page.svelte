<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import EmailModal from '$lib/components/EmailModal.svelte';
    import { user } from '$lib/stores/stores';
    import { ErrorTypes } from '$lib/types/errors';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';

    // loginAttempt state
    let isAttempting = $state(false);
    let showEmailModal = $state(false);

    // email functionality
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

    // password functionality
    let password = $state('');
    let passwordError = $state('');
    function validatePassword(): boolean {
        if (password.length < 1) {
            passwordError = 'Please enter your password';
            return false;
        }
        passwordError = '';
        return true;
    }

    // wrapper to validate all fields at once
    function validateLogin(): boolean {
        const a = validateEmail();
        const b = validatePassword();
        return a && b;
    }

    // authentication functionality
    const url = `/api/v1/auth/login`;
    async function handleLogin(): Promise<void> {
        isAttempting = true;
        try {
            if (!validateLogin()) return;
            const body = { email: email, password: password };
            const response = await fetch(url, {
                body: JSON.stringify(body),
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                // handle the error response sent by the backend
                if (response.status === 429) {
                    toast.error(
                        'You are being rate limited. Please slow down and try again shortly.',
                    );
                    return;
                }
                const body = await response.json();
                switch (body.type) {
                    case ErrorTypes.INVALID_CREDENTIALS:
                        toast.error(body.message);
                        return;
                    case ErrorTypes.SERVER:
                        toast.error(body.message);
                        return;
                    case ErrorTypes.EMAIL_NOT_VERIFIED:
                        showEmailModal = true;
                        return;
                }
            }
            user.set(await response.json());
            goto('/dashboard');
        } catch (err: any) {
            toast.error('An unexpected error occurred, please try again soon.');
        } finally {
            isAttempting = false;
        }
    }

    onMount(() => {
        // handle verified_email query param
        const verified_email = page.url.searchParams.get('verified_email');
        if (!verified_email) {
            return;
        }
        const isTrue = verified_email.toLowerCase() === 'true';
        if (isTrue) {
            toast.success('Email verified! You can now log in.', { duration: Infinity });
        } else {
            toast.error(
                'Your verification link is invalid or has expired. Sign up again with the same email to receive a new one.',
                { duration: Infinity },
            );
        }
        // handle oauth query param
        const errors = page.url.searchParams.get('error');
        if (!errors) {
            return;
        }
        const oauth_failed = errors === 'oauth_failed';
        if (oauth_failed) {
            toast.error(
                'OAuth authentication failed. Please try again or sign up with your email.',
                { duration: Infinity },
            );
        }
    });
    async function handleOAUTH(): Promise<void> {
        window.location.href = '/api/v1/auth/google';
    }
</script>

<main class="flex min-h-screen items-center justify-center bg-background px-4 py-16">
    <div class="w-full max-w-[420px] space-y-3">
        <div class="rounded-2xl border border-border bg-card px-8 py-9">
            <h1 class="mb-1 text-center text-[1.4rem] font-semibold tracking-tight text-foreground">
                Welcome back
            </h1>
            <p class="mb-7 text-center text-sm text-muted-foreground">
                Sign in to continue to your account.
            </p>

            <div class="space-y-4">
                <div class="space-y-1.5">
                    <label for="email" class="block text-sm font-medium text-muted-foreground"
                        >Email</label
                    >
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        onblur={validateEmail}
                        placeholder="you@example.com"
                        disabled={isAttempting}
                        class="w-full rounded-lg border px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none transition bg-background
                            focus:ring-2 focus:ring-primary/20 focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-40
                            {emailError
                            ? 'border-destructive bg-destructive/10 focus:ring-destructive/20 focus:border-destructive'
                            : 'border-border'}"
                    />
                    {#if emailError}
                        <p class="flex items-center gap-1.5 text-xs text-destructive">
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

                <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                        <label
                            for="password"
                            class="block text-sm font-medium text-muted-foreground">Password</label
                        >
                        <a
                            href="/forgot-password"
                            class="text-xs text-muted-foreground transition-colors hover:text-foreground"
                        >
                            Forgot password?
                        </a>
                    </div>
                    <input
                        id="password"
                        type="password"
                        bind:value={password}
                        onblur={validatePassword}
                        placeholder="Your password"
                        disabled={isAttempting}
                        class="w-full rounded-lg border px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none transition bg-background
                            focus:ring-2 focus:ring-primary/20 focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-40
                            {passwordError
                            ? 'border-destructive bg-destructive/10 focus:ring-destructive/20 focus:border-destructive'
                            : 'border-border'}"
                    />
                    {#if passwordError}
                        <p class="flex items-center gap-1.5 text-xs text-destructive">
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
                            {passwordError}
                        </p>
                    {/if}
                </div>

                <button
                    onclick={handleLogin}
                    disabled={isAttempting}
                    class="mt-1 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition
                        hover:bg-primary/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {#if isAttempting}
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
                        Signing in…
                    {:else}
                        Sign in
                    {/if}
                </button>
            </div>

            <div class="my-5 flex items-center gap-3">
                <div class="h-px flex-1 bg-border"></div>
                <span class="text-xs font-medium uppercase tracking-widest text-muted-foreground/50"
                    >or</span
                >
                <div class="h-px flex-1 bg-border"></div>
            </div>

            <button
                onclick={handleOAUTH}
                disabled={isAttempting}
                class="flex w-full items-center gap-3 rounded-lg border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-secondary-foreground transition
                    hover:bg-muted active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
                <svg
                    class="h-4 w-4 shrink-0"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        fill="#4285F4"
                    />
                    <path
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        fill="#34A853"
                    />
                    <path
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                        fill="#FBBC05"
                    />
                    <path
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        fill="#EA4335"
                    />
                </svg>
                Continue with Google
            </button>
        </div>

        <div
            class="rounded-xl border border-border bg-card px-8 py-4 text-center text-sm text-muted-foreground"
        >
            Don't have an account?
            <a
                href="/signup"
                class="ml-1 font-medium text-foreground underline-offset-2 hover:underline hover:text-muted-foreground transition-colors"
            >
                Sign up
            </a>
        </div>

        <p class="text-center text-xs text-muted-foreground">
            <a href="/privacy" class="hover:text-foreground transition-colors">Privacy Policy</a>
            <span class="mx-1.5">·</span>
            <a href="/terms" class="hover:text-foreground transition-colors">Terms of Service</a>
        </p>
    </div>
</main>
<EmailModal
    bind:open={showEmailModal}
    title="Verify your email"
    message={`We've recently sent a verification link to ${email}. Please confirm your email address to activate your account before you can use the app.`}
/>
