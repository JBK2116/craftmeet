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

<header class="fixed top-0 left-0 right-0 z-50 bg-black">
    <nav class="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <!-- Logo -->
        <a href="/" class="flex shrink-0 items-center gap-1.5">
            <img src="/android-chrome-512x512.png" alt="Craftmeet" class="h-7 w-7 invert" />
            <span class="text-sm font-semibold text-white">Craftmeet</span>
        </a>

        <!-- LANDING -->
        {#if isLanding}
            <!-- Desktop nav links -->
            <div class="hidden items-center gap-8 md:flex">
                {#each landingLinks as link}
                    <a
                        href={link.href}
                        class="text-sm text-white/60 transition-colors duration-150 hover:text-white"
                    >
                        {link.title}
                    </a>
                {/each}
            </div>

            <!-- Desktop auth buttons -->
            <div class="hidden items-center gap-3 md:flex">
                <Button
                    variant="ghost"
                    href="/login"
                    class="h-8 px-4 text-sm text-white/70 hover:bg-white/5 hover:text-white"
                >
                    Log in
                </Button>
                <Button
                    href="/signup"
                    class="h-8 rounded-md border border-white/30 bg-white px-4 text-sm text-black transition-all duration-150 hover:border-black/60 hover:bg-white"
                >
                    Sign up
                </Button>
            </div>

            <!-- Mobile hamburger (landing only has real content) -->
            <div class="md:hidden">
                <Sheet>
                    <SheetTrigger>
                        <Button
                            variant="ghost"
                            size="icon"
                            class="h-8 w-8 text-white/60 hover:bg-white/5 hover:text-white"
                        >
                            <Menu class="h-4 w-4" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" class="w-72 border-white/10 bg-black p-6">
                        <div class="mt-8 flex flex-col gap-6">
                            <!-- Nav links -->
                            <div class="flex flex-col gap-4">
                                {#each landingLinks as link}
                                    <a
                                        href={link.href}
                                        class="text-sm text-white/60 transition-colors duration-150 hover:text-white"
                                    >
                                        {link.title}
                                    </a>
                                {/each}
                            </div>
                            <!-- Auth -->
                            <div class="flex flex-col gap-2 border-t border-white/10 pt-4">
                                <Button
                                    variant="ghost"
                                    href="/login"
                                    class="justify-start px-0 text-sm text-white/70 hover:bg-transparent hover:text-white"
                                >
                                    Log in
                                </Button>
                                <Button
                                    href="/signup"
                                    class="border border-white/30 bg-transparent text-sm text-white transition-all duration-150 hover:border-white/60 hover:bg-white/5"
                                >
                                    Sign up
                                </Button>
                            </div>
                        </div>
                    </SheetContent>
                </Sheet>
            </div>

            <!-- AUTH -->
        {:else if isOnboarding}
            <div class="flex items-center gap-3">
                {#if pathname === '/login'}
                    <span class="hidden text-sm text-white/40 sm:inline">No account?</span>
                    <Button
                        href="/signup"
                        class="h-8 rounded-md border border-white/30 bg-white px-4 text-sm text-black transition-all duration-150 hover:border-black/60 hover:bg-white"
                    >
                        Sign up
                    </Button>
                {:else}
                    <span class="hidden text-sm text-white/40 sm:inline">Have an account?</span>
                    <Button
                        variant="ghost"
                        href="/login"
                        class="h-8 px-4 text-sm text-white/70 hover:bg-white/5 hover:text-white"
                    >
                        Log in
                    </Button>
                {/if}
            </div>

            <!-- PUBLIC -->
        {:else if isPublic}
            <Button
                href="/login"
                variant="ghost"
                class="h-8 px-4 text-sm text-white/70 hover:bg-white/5 hover:text-white"
            >
                Log in
            </Button>
            <!-- APP (authenticated) -->
        {:else if isApp}
            <!--
                TODO: Replace placeholder avatar with real user data from auth store.
            -->
            <div class="hidden items-center gap-3 md:flex">
                <Button
                    href="/meetings/create"
                    class="h-8 rounded-md border border-white/30 bg-white px-4 text-sm text-black transition-all duration-150 hover:border-black/60 hover:bg-white"
                >
                    New meeting
                </Button>
                <!-- User avatar wire to auth store -->
                <button
                    class="flex h-8 w-8 items-center justify-center rounded-full border border-white/20 bg-white/10 text-xs font-medium text-white transition hover:bg-white/20"
                    aria-label="Account menu"
                >
                    <!-- TODO: Replace with user initials or avatar image -->
                    U
                </button>
            </div>

            <!-- Mobile: just the avatar (BottomNav handles the rest) -->
            <div class="flex items-center md:hidden">
                <button
                    class="flex h-8 w-8 items-center justify-center rounded-full border border-white/20 bg-white/10 text-xs font-medium text-white transition hover:bg-white/20"
                    aria-label="Account menu"
                >
                    U
                </button>
            </div>
        {/if}
    </nav>
</header>

<!-- Spacer so content doesn't sit under fixed nav -->
<div class="h-14"></div>
