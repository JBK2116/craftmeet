<script lang="ts">
    import Navbar from '$lib/components/Navbar.svelte';
    import { Button } from '$lib/components/ui/button';
    import {
        ChartBarBig,
        ChevronRight,
        CircleCheck,
        LayoutList,
        MessageSquare,
        ThumbsUp,
        Zap,
    } from '@lucide/svelte';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';

    // typewriter effect for "extract hero section"
    let displayed = $state('');
    const word = 'extract';
    let isDeleting = false;

    // run the typewriter effect
    function typewriter() {
        if (isDeleting) {
            displayed = word.substring(0, displayed.length - 1);
            if (displayed.length === 0) isDeleting = false;
        } else {
            displayed = word.substring(0, displayed.length + 1);
            if (displayed.length === word.length) {
                setTimeout(() => {
                    isDeleting = true;
                    typewriter();
                }, 1500);
                return;
            }
        }
        setTimeout(typewriter, isDeleting ? 60 : 100);
    }

    onMount(() => {
        typewriter();
    });

    // join meeting spinner modal
    let modalText = $state('');
    let showModal = $state(false);

    // join meeting functionality
    let code = $state('');
    $effect(() => {
        code = code.replace(/\D/g, '').slice(0, 8);
    });
    // TODO: Update this function to send a join request to the backend
    async function handleJoin(): Promise<void> {
        try {
            modalText = 'Joining meeting';
            showModal = true;
            await new Promise((resolve) => setTimeout(resolve, 1000));
        } catch (err: any) {
        } finally {
            modalText = '';
            showModal = false;
            toast.error('Unable to join meeting', { position: 'bottom-right' });
        }
    }
</script>

<!-- Document Head -->
<svelte:head>
    <title>Craftmeet</title>
    <meta
        name="description"
        content="Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces."
    />
    <link rel="canonical" href="https://craftmeet.com" />
    <meta property="og:title" content="Craftmeet - Structured, Idea-Driven Meetings" />
    <meta
        property="og:description"
        content="Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces."
    />
    <meta property="og:url" content="https://craftmeet.com" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/og-image.png" />
</svelte:head>

<Navbar />
{#if showModal}
    <div
        class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/70 backdrop-blur-sm"
    >
        <div class="flex flex-col items-center gap-4">
            <div
                class="h-8 w-8 rounded-full border-2 border-white/10 border-t-white animate-spin"
            ></div>
            {#if modalText}
                <p class="text-sm text-white/60">{modalText}</p>
            {/if}
        </div>
    </div>
{/if}
<main class="bg-black text-white">
    <!-- Hero -->
    <section
        class="relative flex min-h-[88vh] flex-col items-center justify-center px-6 pt-12 pb-24 text-center overflow-hidden"
    >
        <!-- Subtle radial glow -->
        <div class="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div class="h-150 w-150 rounded-full bg-white/3 blur-3xl"></div>
        </div>

        <!-- Headline -->
        <h1
            class="relative max-w-3xl text-5xl leading-[1.08] tracking-tight text-white/80 sm:text-6xl lg:text-7xl"
        >
            Meetings that
            <span class="inline-block font-black text-white" style="min-width: 3.3ch"
                >{displayed}<span class="animate-pulse">|</span></span
            >
            great ideas.
        </h1>

        <!-- Sub -->
        <p class="relative mt-6 max-w-xl text-base leading-relaxed text-white/40 sm:text-lg">
            Host real-time structured sessions with flexible question formats, live participant
            responses, and an AI-generated summary delivered the moment your meeting ends.
        </p>

        <!-- CTAs -->
        <div class="relative mt-10 flex flex-wrap items-center justify-center gap-3">
            <Button
                href="/login"
                class="h-10 rounded-full bg-white px-6 text-sm font-medium text-black hover:bg-white/90 transition-colors"
            >
                Get started free
            </Button>
            <Button
                variant="ghost"
                href="#join-meeting"
                class="h-10 rounded-full border border-white/15 px-6 text-sm font-medium text-white/70 hover:border-white/30 hover:bg-white/5 hover:text-white transition-all"
            >
                Join a meeting
                <ChevronRight class="ml-1 h-3.5 w-3.5" />
            </Button>
        </div>

        <!-- Social proof -->
        <p class="relative mt-8 text-xs text-white/25">
            No credit card required &nbsp;·&nbsp; Free tier available &nbsp;·&nbsp; No account
            needed to join a meeting
        </p>
    </section>

    <!-- Features -->
    <section id="features" class="border-t border-white/6 px-6 py-24">
        <div class="mx-auto max-w-6xl">
            <div class="mb-16 text-center">
                <p class="mb-3 text-xs uppercase tracking-widest text-white/30">Features</p>
                <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                    Every format your session needs
                </h2>
                <p class="mt-4 text-sm text-white/40 max-w-lg mx-auto leading-relaxed">
                    Six question types built for real facilitation.
                </p>
            </div>

            <div
                class="grid grid-cols-1 gap-px bg-white/6 sm:grid-cols-2 lg:grid-cols-3 rounded-xl overflow-hidden border border-white/6"
            >
                {#each [{ icon: LayoutList, title: 'Multiple Choice', desc: 'Single or multi-select from host-defined options. Results tally in real time.' }, { icon: MessageSquare, title: 'Long Answer', desc: 'Open text responses for qualitative ideas and freeform input.' }, { icon: ChartBarBig, title: 'Ranked Voting', desc: 'Participants drag-rank a priority list. Surface group consensus instantly.' }, { icon: Zap, title: 'Rating Scale', desc: '1–5 or 1–10 numeric rating shown as a live aggregate across the room.' }, { icon: ThumbsUp, title: 'Idea + Upvote', desc: 'Participants submit ideas and the group upvotes anonymously.' }, { icon: CircleCheck, title: 'Yes / No', desc: 'Live pulse check. Instant thumbs up/down read on any question.' }] as feature}
                    <div
                        class="group flex flex-col gap-4 bg-black p-8 transition-colors hover:bg-white/2"
                    >
                        <div
                            class="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5"
                        >
                            <feature.icon class="h-4 w-4 text-white/50" />
                        </div>
                        <div>
                            <h3 class="text-sm font-medium text-white">{feature.title}</h3>
                            <p class="mt-1.5 text-sm leading-relaxed text-white/40">
                                {feature.desc}
                            </p>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </section>

    <!-- How it Works -->
    <section id="how-it-works" class="border-t border-white/6 px-6 py-24">
        <div class="mx-auto max-w-4xl">
            <div class="mb-16 text-center">
                <p class="mb-3 text-xs uppercase tracking-widest text-white/30">How it works</p>
                <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                    From idea to insight in minutes
                </h2>
            </div>

            <div class="relative flex flex-col gap-0">
                <!-- Vertical line -->
                <div class="absolute left-4.75 top-3 bottom-3 w-px bg-white/8 sm:left-5.75"></div>

                {#each [{ step: '01', title: 'Build your session', desc: 'Create a meeting, add questions in any order and format, and set your participant cap. Schedule it ahead or launch immediately.' }, { step: '02', title: 'Share the room', desc: 'Send a link or room code. Participants join instantly!' }, { step: '03', title: 'Run it live', desc: "Open questions one at a time, watch responses stream in, and reveal results when you're ready. You control the pace." }, { step: '04', title: 'Get the summary', desc: 'End the session and receive an AI-generated PDF summarizing every response, idea, and vote from the room.' }] as item}
                    <div class="relative flex gap-8 pb-12 last:pb-0">
                        <!-- Step dot -->
                        <div
                            class="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-black sm:h-12 sm:w-12"
                        >
                            <span class="text-[10px] font-medium text-white/30 sm:text-xs"
                                >{item.step}</span
                            >
                        </div>
                        <div class="pt-2">
                            <h3 class="text-base font-medium text-white sm:text-lg">
                                {item.title}
                            </h3>
                            <p class="mt-2 text-sm leading-relaxed text-white/40 max-w-lg">
                                {item.desc}
                            </p>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </section>

    <!-- Join CTA -->
    <section id="join" class="border-t border-white/6 px-6 py-24">
        <div class="mx-auto max-w-2xl text-center">
            <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Have a room code?
            </h2>
            <p class="mt-4 text-sm leading-relaxed text-white/40">
                Jump straight into an active session. No account needed.
            </p>
            <div class="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                <input
                    type="text"
                    placeholder="Enter room code"
                    maxlength="8"
                    bind:value={code}
                    class="h-10 w-full rounded-full border border-white/10 bg-white/5 px-5 text-sm text-white placeholder-white/25 outline-none transition focus:border-white/25 focus:bg-white/[0.07] sm:w-56"
                />
                <Button
                    id="join-meeting"
                    href="#join-meeting"
                    class="h-10 w-full rounded-full bg-white px-6 text-sm font-medium text-black hover:bg-white/90 sm:w-auto transition-colors"
                    onclick={handleJoin}
                >
                    Join now
                </Button>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="border-t border-white/6 px-6 py-10">
        <div class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
            <span class="text-sm font-medium text-white/40">Craftmeet</span>
            <div class="flex gap-6">
                <a
                    href="/privacy"
                    class="text-xs text-white/40 hover:text-white/70 transition-colors">Privacy</a
                >
                <a href="/terms" class="text-xs text-white/40 hover:text-white/70 transition-colors"
                    >Terms</a
                >
                <a
                    href="/contact"
                    class="text-xs text-white/40 hover:text-white/70 transition-colors">Contact</a
                >
            </div>
            <span class="text-xs text-white/40">© 2026 Craftmeet</span>
        </div>
    </footer>
</main>
