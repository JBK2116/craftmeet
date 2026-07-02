<script lang="ts">
    import { goto } from '$app/navigation';
    import { Button } from '$lib/components/ui/button';
    import {
        ChartBarBig,
        ChevronRight,
        CircleCheck,
        LayoutList,
        MessageSquare,
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
    let name = $state('');
    $effect(() => {
        code = code.replace(/\D/g, '').slice(0, 8);
    });

    async function handleJoin(): Promise<void> {
        if (!code || !name.trim()) {
            toast.error('Please enter a room code and your name.', { position: 'bottom-right' });
            return;
        }
        try {
            modalText = 'Joining meeting…';
            showModal = true;
            // TODO: POST to backend to validate room code and register participant
            // Example:
            // const res = await apiFetch('/api/v1/meetings/join', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ room_code: code, name: name.trim() }),
            // });
            // if (!res.ok) throw new Error('Invalid code');
            // const body = await res.json();
            // goto(`/meetings/${body.meeting_id}/live`);
            await new Promise((resolve) => setTimeout(resolve, 1000));
            modalText = '';
            showModal = false;
        } catch (err: any) {
            modalText = '';
            showModal = false;
            toast.error('Unable to join meeting', { position: 'bottom-right' });
        }
    }
</script>

{#if showModal}
    <div
        class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm"
    >
        <div class="flex flex-col items-center gap-4">
            <div
                class="h-8 w-8 rounded-full border-2 border-muted border-t-primary animate-spin"
            ></div>
            {#if modalText}
                <p class="text-sm text-muted-foreground">{modalText}</p>
            {/if}
        </div>
    </div>
{/if}

<main class="bg-background text-foreground">
    <section
        class="relative flex min-h-[88vh] flex-col items-center justify-center px-6 pt-12 pb-24 text-center overflow-hidden"
    >
        <div class="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div class="h-150 w-150 rounded-full bg-primary/5 blur-3xl"></div>
        </div>

        <h1
            class="relative max-w-3xl text-5xl leading-[1.08] tracking-tight text-foreground/80 sm:text-6xl lg:text-7xl"
        >
            Meetings that
            <span class="inline-block font-black text-primary" style="min-width: 3.3ch">
                {displayed}<span class="animate-pulse">|</span>
            </span>
            great ideas.
        </h1>

        <p
            class="relative mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
            Host real-time structured sessions with flexible question formats, live participant
            responses, and an AI-generated summary delivered the moment your meeting ends.
        </p>

        <div class="relative mt-10 flex flex-wrap items-center justify-center gap-3">
            <Button
                href="/login"
                class="h-10 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 px-6 text-sm font-medium transition-colors"
            >
                Get started free
            </Button>
            <Button
                variant="outline"
                href="#join-meeting"
                class="h-10 rounded-full border-border bg-transparent px-6 text-sm font-medium text-foreground/80 hover:bg-secondary transition-all"
            >
                Join a meeting
                <ChevronRight class="ml-1 h-3.5 w-3.5" />
            </Button>
        </div>

        <p class="relative mt-8 text-xs text-muted-foreground/60">
            No credit card required &nbsp;·&nbsp; Free tier available &nbsp;·&nbsp; No account
            needed to join a meeting
        </p>
    </section>

    <section id="features" class="border-t border-border px-6 py-24">
        <div class="mx-auto max-w-6xl">
            <div class="mb-16 text-center">
                <p class="mb-3 text-xs uppercase tracking-widest text-muted-foreground">Features</p>
                <h2 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                    Every format your session needs
                </h2>
                <p class="mt-4 text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                    Five question types built for real facilitation.
                </p>
            </div>

            <div
                class="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-5 rounded-xl overflow-hidden border border-border"
            >
                {#each [{ icon: LayoutList, title: 'Multiple Choice', desc: 'Single or multi-select from host-defined options. Results tally in real time.' }, { icon: MessageSquare, title: 'Long Answer', desc: 'Open text responses for qualitative ideas and freeform input.' }, { icon: ChartBarBig, title: 'Ranked Voting', desc: 'Participants drag-rank a priority list. Surface group consensus instantly.' }, { icon: Zap, title: 'Rating Scale', desc: '1–5 or 1–10 numeric rating shown as a live aggregate across the room.' }, { icon: CircleCheck, title: 'Yes / No', desc: 'Live pulse check. Instant thumbs up/down read on any question.' }] as feature}
                    <div
                        class="group flex flex-col gap-4 bg-card p-8 transition-colors hover:bg-muted/40"
                    >
                        <div
                            class="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background"
                        >
                            <feature.icon class="h-4 w-4 text-primary" />
                        </div>
                        <div>
                            <h3 class="text-sm font-medium text-foreground">{feature.title}</h3>
                            <p class="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                                {feature.desc}
                            </p>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </section>

    <section id="how-it-works" class="border-t border-border px-6 py-24">
        <div class="mx-auto max-w-4xl">
            <div class="mb-16 text-center">
                <p class="mb-3 text-xs uppercase tracking-widest text-muted-foreground">
                    How it works
                </p>
                <h2 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                    From idea to insight in minutes
                </h2>
            </div>

            <div class="relative flex flex-col gap-0">
                <div class="absolute left-4.75 top-3 bottom-3 w-px bg-border sm:left-5.75"></div>

                {#each [{ step: '01', title: 'Build your session', desc: 'Create a meeting, add questions in any order and format, and set your participant cap. Schedule it ahead or launch immediately.' }, { step: '02', title: 'Share the room', desc: 'Send a link or room code. Participants join instantly!' }, { step: '03', title: 'Run it live', desc: "Open questions one at a time, watch responses stream in, and reveal results when you're ready. You control the pace." }, { step: '04', title: 'Get the summary', desc: 'End the session and receive an AI-generated PDF summarizing every response, idea, and vote from the room.' }] as item}
                    <div class="relative flex gap-8 pb-12 last:pb-0">
                        <div
                            class="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-card sm:h-12 sm:w-12"
                        >
                            <span class="text-[10px] font-medium text-muted-foreground sm:text-xs"
                                >{item.step}</span
                            >
                        </div>
                        <div class="pt-2">
                            <h3 class="text-base font-medium text-foreground sm:text-lg">
                                {item.title}
                            </h3>
                            <p class="mt-2 text-sm leading-relaxed text-muted-foreground max-w-lg">
                                {item.desc}
                            </p>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </section>

    <section id="join" class="border-t border-border px-6 py-24">
        <div class="mx-auto max-w-2xl text-center">
            <h2 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                Have a room code?
            </h2>
            <p class="mt-4 text-sm leading-relaxed text-muted-foreground">
                Jump straight into an active session. No account needed.
            </p>
            <div class="mt-8 flex flex-col items-center gap-3">
                <div class="flex w-full max-w-xs flex-col gap-3 sm:max-w-md sm:flex-row">
                    <input
                        type="text"
                        placeholder="Room code"
                        maxlength="8"
                        bind:value={code}
                        class="h-10 w-full rounded-full border border-border bg-card px-5 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20"
                    />
                    <input
                        type="text"
                        placeholder="Your name"
                        maxlength="50"
                        bind:value={name}
                        class="h-10 w-full rounded-full border border-border bg-card px-5 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20"
                    />
                </div>
                <Button
                    id="join-meeting"
                    href="#join-meeting"
                    class="h-10 w-full max-w-xs rounded-full bg-primary text-primary-foreground hover:bg-primary/90 sm:max-w-md transition-colors"
                    onclick={handleJoin}
                >
                    Join now
                </Button>
            </div>
        </div>
    </section>

    <footer class="border-t border-border px-6 py-10">
        <div class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
            <span class="text-sm font-medium text-muted-foreground">Craftmeet</span>
            <div class="flex gap-6">
                <a
                    href="/privacy"
                    class="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >Privacy</a
                >
                <a
                    href="/terms"
                    class="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >Terms</a
                >
                <a
                    href="/contact"
                    class="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >Contact</a
                >
            </div>
            <span class="text-xs text-muted-foreground">© 2026 Craftmeet</span>
        </div>
    </footer>
</main>
