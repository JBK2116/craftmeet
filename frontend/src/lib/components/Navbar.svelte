<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui/button';
    import { Sheet, SheetContent, SheetTrigger } from '$lib/components/ui/sheet';
    import { Menu } from '@lucide/svelte';

    type NavLink = { title: string; href: string };

    // Route Classification
    const landingRoutes = ['/'];
    const publicRoutes = ['/privacy', '/terms', '/contact'];
    const onBoardingRoutes = ['/login', '/signup', '/forgot-password', '/reset-password'];
    // Everything else is treated as an authenticated app page

    let pathname = $derived(page.url.pathname);

    let isLanding = $derived(landingRoutes.includes(pathname));
    let isPublic = $derived(publicRoutes.includes(pathname));
    let isOnboarding = $derived(onBoardingRoutes.includes(pathname));
    let isApp = $derived(!isLanding && !isOnboarding);

    // Nav Links (landing only)
    const landingLinks: NavLink[] = [
        { title: 'How it Works', href: '#how-it-works' },
        { title: 'Features', href: '#features' },
        { title: 'Pricing', href: '/pricing' },
        { title: 'Join Meeting', href: '#join-meeting' },
    ];
</script>

<header class="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background">
    <nav class="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <a href="/" class="flex shrink-0 items-center gap-1.5">
            <img src="/android-chrome-512x512.png" alt="Craftmeet" class="h-7 w-7 dark:invert" />
            <span class="text-sm font-semibold text-foreground">Craftmeet</span>
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
                                <Button
                                    variant="ghost"
                                    href="/login"
                                    class="justify-start px-0 text-sm text-muted-foreground hover:bg-transparent hover:text-foreground"
                                >
                                    Log in
                                </Button>
                                <Button
                                    variant="outline"
                                    href="/signup"
                                    class="text-sm text-foreground transition-all duration-150 hover:bg-accent"
                                >
                                    Sign up
                                </Button>
                            </div>
                        </div>
                    </SheetContent>
                </Sheet>
            </div>
        {:else if isOnboarding}
            <div class="flex items-center gap-3">
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
            <Button
                href="/login"
                variant="ghost"
                class="h-8 px-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
                Log in
            </Button>
        {:else if isApp}
            <div class="hidden items-center gap-3 md:flex">
                <Button
                    href="/meetings/create"
                    class="h-8 rounded-md bg-primary px-4 text-sm text-primary-foreground transition-all duration-150 hover:bg-primary/90"
                >
                    New meeting
                </Button>
                <button
                    class="flex h-8 w-8 items-center justify-center rounded-full border border-input bg-muted text-xs font-medium text-muted-foreground transition hover:bg-muted/80"
                    aria-label="Account menu"
                >
                    U
                </button>
            </div>

            <div class="flex items-center md:hidden">
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
