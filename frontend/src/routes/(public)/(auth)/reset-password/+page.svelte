<script lang="ts">
    import { page } from '$app/state';
    import { ErrorTypes } from '$lib/types/errors';
    import { toast } from 'svelte-sonner';

    // resetAttempt state
    let isAttempting = $state(false);

    // e.g. GET /reset-password?token=<token>
    let resetToken = $derived(page.url.searchParams.get('token') ?? '');

    // password functionality
    let password = $state('');
    let passwordError = $state('');
    function validatePassword(): boolean {
        const MIN = 12;
        const MAX = 64;
        // length check
        let lengthOkay = password.length >= MIN && password.length <= MAX;
        if (!lengthOkay) {
            passwordError = 'Password must be between 12 to 64 characters';
            return false;
        }
        // invalid symbol check
        let symbolsOkay = !/[\u0000-\u001F\u007F]/.test(password);
        if (!symbolsOkay) {
            passwordError = 'Password contains an invalid symbol';
            return false;
        }
        passwordError = '';
        return true;
    }

    // confirm password functionality
    let confirmPassword = $state('');
    let confirmPasswordError = $state('');
    function validateConfirmPassword(): boolean {
        if (confirmPassword !== password) {
            confirmPasswordError = 'Passwords do not match';
            return false;
        }
        confirmPasswordError = '';
        return true;
    }

    // wrapper to validate all fields at once
    function validateReset(): boolean {
        const a = validatePassword();
        const b = validateConfirmPassword();
        return a && b;
    }

    // reset functionality
    const url = `/api/v1/auth/reset-password`;
    async function handleReset(): Promise<void> {
        isAttempting = true;
        try {
            if (!resetToken) {
                toast.error('Invalid or missing reset token', { duration: Infinity });
                return;
            }
            if (!validateReset()) return;
            const body = {
                token: resetToken,
                password: password,
                confirm_password: confirmPassword,
            };
            const headers = { 'Content-Type': 'application/json' };
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(body),
            });
            if (!response.ok) {
                const body = await response.json();
                switch (body.type) {
                    case ErrorTypes.TOKEN:
                        toast.error('Invalid or missing reset token', {
                            position: 'bottom-right',
                            duration: Infinity,
                        });
                        return;
                    case ErrorTypes.PASSWORD:
                        passwordError = body.message;
                        return;
                    case ErrorTypes.CONFIRM_PASSWORD:
                        confirmPasswordError = body.message;
                        return;
                    case ErrorTypes.BODY:
                        passwordError = body.message;
                        return;
                    case ErrorTypes.SERVER:
                        toast.error(body.message, { duration: Infinity });
                        return;
                }
            }
            toast.success('Password updated please sign in.', { duration: Infinity });
        } catch (err: any) {
            toast.error('Unable to reset password', { duration: Infinity });
        } finally {
            isAttempting = false;
        }
    }
</script>

<svelte:head>
    <title>Reset Password - Craftmeet</title>
    <meta
        name="description"
        content="Reset your Craftmeet account password and regain access to your meetings."
    />
    <link rel="canonical" href="https://craftmeet.com/reset-password" />
    <meta property="og:title" content="Craftmeet - Reset Password" />
    <meta
        property="og:description"
        content="Reset your Craftmeet account password and regain access to your meetings."
    />
    <meta property="og:url" content="https://craftmeet.com/reset-password" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/og-image.png" />
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-6 py-24">
    <div class="w-full max-w-md space-y-3">
        <div class="rounded-2xl border border-border bg-card px-8 py-9 shadow-sm">
            <h1 class="mb-1 text-center text-2xl font-semibold tracking-tight text-foreground">
                Reset your password
            </h1>
            <p class="mb-7 text-center text-sm text-muted-foreground">
                Choose a strong password to secure your account.
            </p>

            <div class="space-y-4">
                <div class="space-y-1.5">
                    <label for="password" class="block text-sm font-medium text-muted-foreground">
                        New Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        bind:value={password}
                        onblur={validatePassword}
                        placeholder="12+ characters"
                        disabled={isAttempting}
                        class="w-full rounded-lg border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition
                            focus:ring-1 focus:ring-ring focus:border-ring disabled:cursor-not-allowed disabled:opacity-40
                            {passwordError
                            ? 'border-destructive/60 bg-destructive/10 focus:ring-destructive/40 focus:border-destructive/40'
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

                <div class="space-y-1.5">
                    <label
                        for="confirm-password"
                        class="block text-sm font-medium text-muted-foreground"
                    >
                        Confirm New Password
                    </label>
                    <input
                        id="confirm-password"
                        type="password"
                        bind:value={confirmPassword}
                        onblur={validateConfirmPassword}
                        oninput={validateConfirmPassword}
                        placeholder="Re-enter your password"
                        disabled={isAttempting}
                        class="w-full rounded-lg border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition
                            focus:ring-1 focus:ring-ring focus:border-ring disabled:cursor-not-allowed disabled:opacity-40
                            {confirmPasswordError
                            ? 'border-destructive/60 bg-destructive/10 focus:ring-destructive/40 focus:border-destructive/40'
                            : 'border-border'}"
                    />
                    {#if confirmPasswordError}
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
                            {confirmPasswordError}
                        </p>
                    {/if}
                </div>

                <button
                    onclick={handleReset}
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
                        Resetting password…
                    {:else}
                        Reset password
                    {/if}
                </button>
            </div>
        </div>

        <div
            class="rounded-xl border border-border bg-card px-8 py-4 text-center text-sm text-muted-foreground shadow-sm"
        >
            Remember your password?
            <a
                href="/login"
                class="ml-1 font-medium text-foreground underline-offset-2 hover:underline hover:text-muted-foreground transition-colors"
            >
                Sign in
            </a>
        </div>

        <p class="text-center text-xs text-muted-foreground">
            <a href="/privacy" class="hover:text-foreground transition-colors">Privacy Policy</a>
            <span class="mx-1.5">·</span>
            <a href="/terms" class="hover:text-foreground transition-colors">Terms of Service</a>
        </p>
    </div>
</main>
