<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { CircleCheck } from '@lucide/svelte';

    const features = [
        'Unlimited meetings',
        'All 5 question formats',
        'Live participant responses',
        'AI-generated summary after every session',
        'No account needed to join a meeting',
    ];
</script>

<main class="bg-background text-foreground">
    <section class="flex min-h-screen flex-col items-center justify-center px-6 py-24">
        <div class="mb-10 text-center">
            <p class="mb-3 text-xs uppercase tracking-widest text-muted-foreground">Pricing</p>
            <h1 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                Free With No Catch.
            </h1>
            <p class="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
                Craftmeet is free while we build. No credit card required, no seat limits, no paywalled
                features.
            </p>
        </div>

        <div class="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card">
            <div class="flex items-baseline gap-1.5">
                <span class="text-4xl font-bold tracking-tight text-foreground">$0</span>
                <span class="text-sm text-muted-foreground">/ forever</span>
            </div>

            <ul class="mt-6 space-y-3">
                {#each features as feature}
                    <li class="flex items-start gap-2.5 text-sm text-muted-foreground">
                        <CircleCheck class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        {feature}
                    </li>
                {/each}
            </ul>

            <Button
                href="/login"
                class="mt-8 h-10 w-full rounded-full bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors"
            >
                Get started free
            </Button>
        </div>

        <p class="mt-8 text-xs text-muted-foreground/60">
            Pricing may change as we grow, early users receive notice first.
        </p>
    </section>
</main>
