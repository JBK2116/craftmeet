<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui/button';
    import { Sheet, SheetContent, SheetTrigger } from '$lib/components/ui/sheet';
    import { Menu } from '@lucide/svelte';

    type NavLink = { title: string; href: string };

    const landingLinks: NavLink[] = [
        { title: 'How it Works', href: '#how-it-works' },
        { title: 'Features', href: '#features' },
        { title: 'Pricing', href: '/pricing' },
    ];
    // TODO: Update the Login and Signup buttons to be only displayed if the user isn't authenticated
    const authRoutes = ['/', '/login', '/signup'];
    // page is more robust than window.location.href
    let pathname = $derived(page.url.pathname);
    // determine what page is active
    let isLandingPage = $derived(pathname === '/');
    let isAuthPage = $derived(authRoutes.includes(pathname));
    // conditional showcasing
    let navLinks = $derived(isLandingPage ? landingLinks : []);
</script>

<header class="fixed top-0 left-0 right-0 z-50 bg-black backdrop-blur-sm">
    <nav class="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <!-- Logo -->
        <a href="/" class="flex gap-1 items-center shrink-0">
            <img src="/android-chrome-512x512.png" alt="Craftmeet" class="h-7 w-7 invert" />
            <p class="text-white">Craftmeet</p>
        </a>
        <!-- Center Nav -->
        <div class="hidden md:flex items-center gap-8">
            {#each navLinks as link}
                <a
                    href={link.href}
                    class="text-sm text-white/60 hover:text-white transition-colors duration-150"
                >
                    {link.title}
                </a>
            {/each}

            {#if isLandingPage}
                <a
                    href="#join-meeting"
                    class="text-sm text-white/60 hover:text-white transition-colors duration-150"
                >
                    Join Meeting
                </a>
            {/if}
        </div>

        <!-- Right Actions -->
        {#if isAuthPage}
            <div class="hidden md:flex items-center gap-3">
                <!-- TODO: Implement this login HREF on the frontend -->
                <Button
                    variant="ghost"
                    href="/login"
                    class="text-sm text-white/70 hover:text-white hover:bg-white/5 px-4 h-8"
                >
                    Log in
                </Button>

                <!-- TODO: Implement this signup HREF on the frontend -->
                <Button
                    href="/signup"
                    class="text-sm bg-white border border-white/30 hover:bg-white hover:border-black/60 text-black px-4 h-8 rounded-md transition-all duration-150"
                >
                    Sign up
                </Button>
            </div>
        {/if}

        <!-- Mobile Menu -->
        <div class="md:hidden">
            <Sheet>
                <SheetTrigger>
                    <Button
                        variant="ghost"
                        size="icon"
                        class="text-white/60 hover:text-white hover:bg-white/5 h-8 w-8"
                    >
                        <Menu class="h-4 w-4" />
                    </Button>
                </SheetTrigger>
                <SheetContent side="right" class="bg-black border-white/10 w-72 p-6">
                    <div class="flex flex-col gap-6 mt-8">
                        <div class="flex flex-col gap-4">
                            {#each navLinks as link}
                                <a
                                    href={link.href}
                                    class="text-sm text-white/60 hover:text-white transition-colors duration-150"
                                >
                                    {link.title}
                                </a>
                            {/each}
                            {#if isLandingPage}
                                <a
                                    href="#join-meeeing"
                                    class="text-sm text-white/60 hover:text-white transition-colors duration-150"
                                >
                                    Join Meeting
                                </a>
                            {/if}
                        </div>
                        {#if isAuthPage}
                            <div class="flex flex-col gap-2 pt-4 border-t border-white/10">
                                <Button
                                    variant="ghost"
                                    href="/login"
                                    class="justify-start text-sm text-white/70 hover:text-white hover:bg-white/5 px-0"
                                >
                                    Log in
                                </Button>
                                <Button
                                    href="/signup"
                                    class="text-sm bg-transparent border border-white/30 hover:border-white/60 hover:bg-white/5 text-white transition-all duration-150"
                                >
                                    Sign up
                                </Button>
                            </div>
                        {/if}
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    </nav>
</header>

<!-- Spacer so content doesn't sit under fixed nav -->
<div class="h-14"></div>
