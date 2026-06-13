<script lang="ts">
    import { Badge } from '$lib/components/ui/badge/index.js';
    import { buttonVariants } from '$lib/components/ui/button/index.js';
    import * as Card from '$lib/components/ui/card/index.js';
</script>

<main class="relative min-h-screen bg-background text-foreground">
    <!-- Decorative background glow utilizing token safe opacity variables -->
    <div class="pointer-events-none absolute inset-0 flex justify-center overflow-hidden">
        <div class="h-[800px] w-[800px] -translate-y-1/2 rounded-full bg-primary/5 blur-3xl"></div>
    </div>

    <div class="mx-auto flex max-w-3xl flex-col gap-12 px-6 py-24 lg:px-8">
        <!-- Page Header -->
        <header class="flex flex-col gap-4">
            <h1 class="text-4xl font-semibold tracking-tight text-foreground">Contact Us</h1>
            <p class="text-lg text-muted-foreground">
                Have a question, a piece of feedback, or need a hand with your account? We'd love to
                hear from you.
            </p>
            <p class="text-muted-foreground">
                The only way to reach us is by email. We don't operate a phone line or a physical
                office, so emailing us directly at
                <a
                    href="mailto:support@craftmeet.com"
                    class="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground"
                    >support@craftmeet.com</a
                >
                is the fastest and only way to get a response. This is the same address referenced throughout
                our
                <a
                    href="/privacy"
                    class="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground"
                    >Privacy Notice</a
                >
                and
                <a
                    href="/terms"
                    class="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground"
                    >Terms and Conditions</a
                >.
            </p>
        </header>

        <!-- Contact Methods -->
        <div class="flex flex-col gap-6">
            <!-- Email the primary (and only) contact method -->
            <Card.Root class="ring-foreground/10">
                <Card.Header>
                    <Card.Title class="text-lg">Email Us Directly</Card.Title>
                    <Card.Description>
                        Email is our primary and only support channel. Whether it's a general
                        question, a privacy request, a billing concern, or a legal inquiry, send it
                        our way and we'll get back to you.
                    </Card.Description>
                </Card.Header>
                <Card.Content class="flex flex-col gap-4">
                    <a
                        href="mailto:support@craftmeet.com"
                        class={buttonVariants({ variant: 'default' }) + ' w-fit'}
                    >
                        support@craftmeet.com
                    </a>
                    <p class="text-sm text-muted-foreground">
                        We aim to respond to all legitimate requests within 30 days.
                    </p>
                </Card.Content>
            </Card.Root>

            <!-- Mailing Address not yet available -->
            <Card.Root class="ring-foreground/10">
                <Card.Header>
                    <Card.Title class="flex items-center gap-2 text-lg">
                        Mailing Address
                        <Badge variant="secondary">Coming Soon</Badge>
                    </Card.Title>
                    <Card.Description>
                        We don't currently have a physical or virtual mailing address. Once we
                        establish one, you'll be able to find it here.
                    </Card.Description>
                </Card.Header>
                <Card.Content>
                    <p class="text-sm text-muted-foreground">
                        In the meantime, please direct all correspondence to
                        <a
                            href="mailto:support@craftmeet.com"
                            class="font-medium text-foreground underline underline-offset-4 hover:text-muted-foreground"
                            >support@craftmeet.com</a
                        >.
                    </p>
                </Card.Content>
            </Card.Root>
        </div>
    </div>
</main>
