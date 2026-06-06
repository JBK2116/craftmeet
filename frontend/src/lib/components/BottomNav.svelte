<script lang="ts">
    import { page } from '$app/state';
    import { CirclePlus, LayoutDashboard, LogIn, User } from '@lucide/svelte';

    type BottomNavItem = { title: string; href: string; icon: typeof LayoutDashboard };

    const items: BottomNavItem[] = [
        { title: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
        { title: 'New Meeting', href: '/meetings/create', icon: CirclePlus },
        { title: 'Join', href: '/join', icon: LogIn },
        { title: 'Account', href: '/account', icon: User },
    ];

    // Route Classification (mirrors Navbar.svelte)
    // Keep these in sync with Navbar if routes are added to any category.
    const landingRoutes = ['/'];
    const onboardingRoutes = ['/login', '/signup', '/forgot-password', '/reset-password'];
    const publicRoutes = ['/privacy', '/terms', '/contact'];

    let pathname = $derived(page.url.pathname);

    // Only render on authenticated app pages
    let isApp = $derived(
        !landingRoutes.includes(pathname) &&
            !onboardingRoutes.includes(pathname) &&
            !publicRoutes.includes(pathname),
    );
</script>

{#if isApp}
    <nav
        class="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
        aria-label="Mobile navigation"
    >
        <div class="flex h-16 items-stretch">
            {#each items as item}
                {@const isActive = pathname === item.href || pathname.startsWith(item.href + '/')}
                <a
                    href={item.href}
                    class="flex flex-1 flex-col items-center justify-center gap-1 transition-colors duration-150
                        {isActive
                        ? 'text-foreground'
                        : 'text-muted-foreground/60 hover:text-foreground/80'}"
                    aria-current={isActive ? 'page' : undefined}
                >
                    <item.icon class="h-5 w-5 shrink-0" />
                    <span class="text-[10px] font-medium tracking-wide">{item.title}</span>
                </a>
            {/each}
        </div>
    </nav>

    <div class="h-16 pb-[env(safe-area-inset-bottom)] md:hidden"></div>
{/if}
