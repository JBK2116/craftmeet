<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui/button';
    import { Sheet, SheetContent, SheetTrigger } from '$lib/components/ui/sheet';
    import { user } from '$lib/stores/stores';
    import { Menu, Moon, Sun } from '@lucide/svelte';

    import Logo from './Logo.svelte';

    type NavLink = { title: string; href: string };

    // Route Classification
    const landingRoutes = ['/'];
    const publicRoutes = ['/privacy', '/terms', '/contact'];
    const onBoardingRoutes = ['/login', '/signup', '/forgot-password', '/reset-password'];

    let pathname = $derived(page.url.pathname);

    let isLanding = $derived(landingRoutes.includes(pathname));
    let isPublic = $derived(publicRoutes.includes(pathname));
    let isOnboarding = $derived(onBoardingRoutes.includes(pathname));
    let isApp = $derived(!isLanding && !isOnboarding);

    const landingLinks: NavLink[] = [
        { title: 'How it Works', href: '#how-it-works' },
        { title: 'Features', href: '#features' },
        { title: 'Pricing', href: '/pricing' },
        { title: 'Join Meeting', href: '#join-meeting' },
    ];

    // Theme toggle
    let isDark = $state(
        typeof document !== 'undefined'
            ? document.documentElement.classList.contains('dark')
            : false,
    );

    function toggleTheme() {
        isDark = !isDark;
        document.documentElement.classList.toggle('dark', isDark);
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }
</script>

<header class="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background">
    <nav class="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <a
            href="/"
            class="group flex shrink-0 items-center gap-2 text-foreground transition-opacity active:opacity-90"
        >
            <Logo
                class="h-6 w-6 text-foreground transition-colors duration-200 group-hover:text-primary"
            />
            <span
                class="text-sm font-semibold tracking-tight transition-colors duration-200 group-hover:text-foreground/90"
            >
                Craftmeet
            </span>
        </a>

        {#if isLanding}
            <div class="hidden items-center gap-8 md:flex">
                {#each landingLinks as link}
                    <a
                        href={link.href}
                        class="text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
                    >
                        {link.title}
                    </a>
                {/each}
            </div>

            <div class="hidden items-center gap-3 md:flex">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={toggleTheme}
                    class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Toggle theme"
                >
                    {#if isDark}
                        <Sun class="h-4 w-4" />
                    {:else}
                        <Moon class="h-4 w-4" />
                    {/if}
                </Button>
                {#if $user}
                    <Button
                        variant="ghost"
                        href="/dashboard"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Dashboard
                    </Button>
                {:else}
                    <Button
                        variant="ghost"
                        href="/login"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Log in
                    </Button>
                    <Button
                        href="/signup"
                        class="h-8 rounded-md bg-primary px-4 text-sm text-primary-foreground transition-all duration-150 hover:bg-primary/90"
                    >
                        Sign up
                    </Button>
                {/if}
            </div>

            <div class="md:hidden">
                <Sheet>
                    <SheetTrigger>
                        <Button
                            variant="ghost"
                            size="icon"
                            class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        >
                            <Menu class="h-4 w-4" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" class="w-72 border-border bg-background p-6">
                        <div class="mt-8 flex flex-col gap-6">
                            <div class="flex flex-col gap-4">
                                {#each landingLinks as link}
                                    <a
                                        href={link.href}
                                        class="text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
                                    >
                                        {link.title}
                                    </a>
                                {/each}
                            </div>
                            <div class="flex flex-col gap-2 border-t border-border pt-4">
                                {#if $user}
                                    <Button
                                        variant="ghost"
                                        href="/dashboard"
                                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                    >
                                        Dashboard
                                    </Button>
                                {:else}
                                    <Button
                                        variant="ghost"
                                        href="/login"
                                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                    >
                                        Log in
                                    </Button>
                                    <Button
                                        href="/signup"
                                        class="h-8 rounded-md bg-primary px-4 text-sm text-primary-foreground transition-all duration-150 hover:bg-primary/90"
                                    >
                                        Sign up
                                    </Button>
                                {/if}
                                <button
                                    onclick={toggleTheme}
                                    class="flex items-center gap-2 pt-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                                    aria-label="Toggle theme"
                                >
                                    {#if isDark}
                                        <Sun class="h-4 w-4" /> Light mode
                                    {:else}
                                        <Moon class="h-4 w-4" /> Dark mode
                                    {/if}
                                </button>
                            </div>
                        </div>
                    </SheetContent>
                </Sheet>
            </div>
        {:else if isOnboarding}
            <div class="flex items-center gap-3">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={toggleTheme}
                    class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Toggle theme"
                >
                    {#if isDark}
                        <Sun class="h-4 w-4" />
                    {:else}
                        <Moon class="h-4 w-4" />
                    {/if}
                </Button>
                {#if pathname === '/login'}
                    <span class="hidden text-sm text-muted-foreground/80 sm:inline"
                        >No account?</span
                    >
                    <Button
                        href="/signup"
                        class="h-8 rounded-md bg-primary px-4 text-sm text-primary-foreground transition-all duration-150 hover:bg-primary/90"
                    >
                        Sign up
                    </Button>
                {:else if pathname === '/forgot-password'}
                    <span class="hidden text-sm text-muted-foreground/80 sm:inline"
                        >Back to login?</span
                    >
                    <Button
                        variant="ghost"
                        href="/login"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Log in
                    </Button>
                {:else if pathname === '/reset-password'}
                    <span class="hidden text-sm text-muted-foreground/80 sm:inline"
                        >Back to login?</span
                    >
                    <Button
                        variant="ghost"
                        href="/login"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Log in
                    </Button>
                {:else}
                    <span class="hidden text-sm text-muted-foreground/80 sm:inline"
                        >Have an account?</span
                    >
                    <Button
                        variant="ghost"
                        href="/login"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Log in
                    </Button>
                {/if}
            </div>
        {:else if isPublic}
            <div class="flex items-center gap-3">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={toggleTheme}
                    class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Toggle theme"
                >
                    {#if isDark}
                        <Sun class="h-4 w-4" />
                    {:else}
                        <Moon class="h-4 w-4" />
                    {/if}
                </Button>
                {#if $user}
                    <Button
                        href="/dashboard"
                        variant="ghost"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Dashboard
                    </Button>
                {:else}
                    <Button
                        href="/login"
                        variant="ghost"
                        class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    >
                        Log in
                    </Button>
                {/if}
            </div>
        {:else if isApp}
            <div class="hidden items-center gap-3 md:flex">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={toggleTheme}
                    class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Toggle theme"
                >
                    {#if isDark}
                        <Sun class="h-4 w-4" />
                    {:else}
                        <Moon class="h-4 w-4" />
                    {/if}
                </Button>
                <button
                    class="flex h-8 w-8 items-center justify-center rounded-full border border-input bg-muted text-xs font-medium text-muted-foreground transition hover:bg-muted/80"
                    aria-label="Account menu"
                >
                    U
                </button>
            </div>

            <div class="flex items-center gap-2 md:hidden">
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={toggleTheme}
                    class="h-8 w-8 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Toggle theme"
                >
                    {#if isDark}
                        <Sun class="h-4 w-4" />
                    {:else}
                        <Moon class="h-4 w-4" />
                    {/if}
                </Button>
                <button
                    class="flex h-8 w-8 items-center justify-center rounded-full border border-input bg-muted text-xs font-medium text-muted-foreground transition hover:bg-muted/80"
                    aria-label="Account menu"
                >
                    U
                </button>
            </div>
        {/if}
    </nav>
</header>

<div class="h-14"></div>
