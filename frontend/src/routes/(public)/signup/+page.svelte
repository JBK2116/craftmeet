<script lang="ts">
    import EmailModal from '$lib/components/EmailModal.svelte';
    import { ErrorTypes } from '$lib/types/errors';
    import { toast } from 'svelte-sonner';

    // signupAttempt state
    let isAttempting = $state(false);
    let showSuccessModal = $state(false);

    // username functionality
    let username = $state('');
    let nameError = $state('');
    function validateName(): boolean {
        // Length: 3–20
        if (username.length < 3 || username.length > 20) {
            nameError = 'Username must be between 3 and 20 characters';
            return false;
        }
        // Must start with a letter
        if (!/^[a-zA-Z]/.test(username)) {
            nameError = 'Username must start with a letter';
            return false;
        }
        // Allowed chars: letters, numbers, _, -
        if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
            nameError = 'Username can only contain letters, numbers, underscores, and hyphens';
            return false;
        }
        // Cannot end with separator
        if (/[_-]$/.test(username)) {
            nameError = 'Username cannot end with an underscore or hyphen';
            return false;
        }
        // No consecutive or mixed separators
        if (/(__|--|_-|-_)/.test(username)) {
            nameError = 'Username cannot contain consecutive underscores or hyphens';
            return false;
        }
        nameError = '';
        return true;
    }

    // email functionality
    let email = $state('');
    let emailError = $state('');
    function validateEmail(): boolean {
        const value = email.trim();
        // Length limits (RFC practical limits)
        if (value.length < 3 || value.length > 254) {
            emailError = 'Email address length is invalid';
            return false;
        }
        // Basic structure
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            emailError = 'Please enter a valid email address';
            return false;
        }
        // Prevent consecutive dots
        if (value.includes('..')) {
            emailError = 'Email cannot contain consecutive periods';
            return false;
        }
        const [local, domain] = value.split('@');
        if (local.length > 64) {
            emailError = 'Email username portion is too long';
            return false;
        }
        // Domain labels: no "-example" or "example-"
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

    // wrapper to validate all fields at once
    function validateSignup(): boolean {
        const a = validateName();
        const b = validateEmail();
        const c = validatePassword();
        return a && b && c;
    }

    // authentication functionality
    const url = `/api/v1/auth/signup`;
    async function handleSignup(): Promise<void> {
        isAttempting = true;
        try {
            if (!validateSignup()) return;
            const body = { username: username, email: email, password: password };
            const response = await fetch(url, {
                body: JSON.stringify(body),
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                // handle the error response sent by the backend
                const body = await response.json();
                switch (body.type) {
                    case ErrorTypes.USERNAME:
                        nameError = body.message;
                        return;
                    case ErrorTypes.EMAIL:
                        emailError = body.message;
                        return;
                    case ErrorTypes.PASSWORD:
                        passwordError = body.message;
                        return;
                    case ErrorTypes.SERVER:
                        toast.error(`Server Error: ${body.message}`);
                        return;
                }
            }
            showSuccessModal = true;
            return;
        } catch (err: any) {
            toast.error('An unexpected error occurred, please try again soon.');
            return;
        } finally {
            isAttempting = false;
        }
    }
    async function handleOAUTH(): Promise<void> {
        // TODO: Handle this function later
        isAttempting = true;
        try {
            await new Promise((resolve) => setTimeout(resolve, 1000));
        } catch (err: any) {
        } finally {
            toast.error('Unable to signup', { position: 'bottom-right' });
            isAttempting = false;
        }
    }
</script>

<svelte:head>
    <title>Sign Up - Craftmeet</title>
    <meta
        name="description"
        content="Create your Craftmeet account and start hosting real-time structured meetings with AI-generated summaries."
    />
    <link rel="canonical" href="https://craftmeet.com/signup" />
    <meta property="og:title" content="Craftmeet - Sign Up" />
    <meta
        property="og:description"
        content="Create your Craftmeet account and start hosting real-time structured meetings with AI-generated summaries."
    />
    <meta property="og:url" content="https://craftmeet.com/signup" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/og-image.png" />
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-6 py-24">
    <div class="w-full max-w-md space-y-3">
        <div class="rounded-2xl border border-border bg-card px-8 py-9 shadow-sm">
            <h1 class="mb-1 text-center text-2xl font-semibold tracking-tight text-foreground">
                Create your account
            </h1>
            <p class="mb-7 text-center text-sm text-muted-foreground">
                Start running better meetings today.
            </p>

            <div class="space-y-4">
                <div class="space-y-1.5">
                    <label for="username" class="block text-sm font-medium text-muted-foreground">
                        Username
                    </label>
                    <input
                        id="username"
                        type="text"
                        bind:value={username}
                        onblur={validateName}
                        placeholder="yourname"
                        disabled={isAttempting}
                        class="w-full rounded-lg border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition
                            focus:ring-1 focus:ring-ring focus:border-ring disabled:cursor-not-allowed disabled:opacity-40
                            {nameError
                            ? 'border-destructive/60 bg-destructive/10 focus:ring-destructive/40 focus:border-destructive/40'
                            : 'border-border'}"
                    />
                    {#if nameError}
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
                            {nameError}
                        </p>
                    {/if}
                </div>

                <div class="space-y-1.5">
                    <label for="email" class="block text-sm font-medium text-muted-foreground">
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        onblur={validateEmail}
                        placeholder="you@example.com"
                        disabled={isAttempting}
                        class="w-full rounded-lg border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition
                            focus:ring-1 focus:ring-ring focus:border-ring disabled:cursor-not-allowed disabled:opacity-40
                            {emailError
                            ? 'border-destructive/60 bg-destructive/10 focus:ring-destructive/40 focus:border-destructive/40'
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
                    <label for="password" class="block text-sm font-medium text-muted-foreground">
                        Password
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

                <button
                    onclick={handleSignup}
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
                        Creating account…
                    {:else}
                        Create account
                    {/if}
                </button>
            </div>

            <div class="my-5 flex items-center gap-3">
                <div class="h-px flex-1 bg-border"></div>
                <span class="text-xs font-medium uppercase tracking-widest text-muted-foreground"
                    >or</span
                >
                <div class="h-px flex-1 bg-border"></div>
            </div>

            <button
                onclick={handleOAUTH}
                disabled={isAttempting}
                class="flex w-full items-center justify-center gap-3 rounded-lg border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-secondary-foreground transition
                    hover:bg-secondary/80 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
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
            class="rounded-xl border border-border bg-card px-8 py-4 text-center text-sm text-muted-foreground shadow-sm"
        >
            Already have an account?
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

<EmailModal
    bind:open={showSuccessModal}
    title="Verify your email"
    message={`We've sent a verification link to ${email}. Please confirm your email address to activate your account before you can use the app.`}
/>
