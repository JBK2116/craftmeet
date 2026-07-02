<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { LogIn, Plus, X } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';

    let showModal = $state(false);
    let code = $state('');
    let name = $state('');
    let loading = $state(false);

    $effect(() => {
        code = code.replace(/\D/g, '').slice(0, 8);
    });

    function close() {
        if (loading) return;
        showModal = false;
        code = '';
        name = '';
    }

    async function handleJoin() {
        if (!code || !name.trim()) {
            toast.error('Please enter a room code and your name.');
            return;
        }
        loading = true;
        try {
            // TODO: POST to backend to validate room code and register participant
            // const res = await fetch('/api/v1/meetings/join', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ room_code: code, name: name.trim() }),
            // });
            // if (!res.ok) throw new Error('Invalid code');
            // const body = await res.json();
            // goto(`/meetings/${body.meeting_id}/live`);
            await new Promise((resolve) => setTimeout(resolve, 1000));
            close();
        } catch {
            toast.error('Unable to join meeting.');
        } finally {
            loading = false;
        }
    }
</script>

{#if showModal}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        role="button"
        tabindex="0"
        class="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm"
        onclick={close}
        onkeydown={(e) => e.key === 'Escape' && close()}
    >
        <div
            role="dialog"
            aria-modal="true"
            tabindex="-1"
            class="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-lg"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.key === 'Escape' && close()}
        >
            <div class="mb-4 flex items-center justify-between">
                <h2 class="text-base font-semibold text-foreground">Join a Meeting</h2>
                <button
                    type="button"
                    onclick={close}
                    class="rounded-lg p-1 text-muted-foreground transition hover:bg-accent hover:text-foreground"
                >
                    <X class="h-4 w-4" />
                </button>
            </div>

            <div class="flex flex-col gap-3">
                <input
                    type="text"
                    placeholder="Room code"
                    maxlength="8"
                    bind:value={code}
                    disabled={loading}
                    class="h-10 w-full rounded-lg border border-border bg-background px-4 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20"
                />
                <input
                    type="text"
                    placeholder="Your name"
                    maxlength="50"
                    bind:value={name}
                    disabled={loading}
                    class="h-10 w-full rounded-lg border border-border bg-background px-4 text-sm text-foreground placeholder-muted-foreground outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/20"
                />
                <Button class="h-10 w-full rounded-lg" onclick={handleJoin} disabled={loading}>
                    {#if loading}
                        <div
                            class="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin"
                        ></div>
                    {:else}
                        Join
                    {/if}
                </Button>
            </div>
        </div>
    </div>
{/if}

<!-- quick actions for create meeting and join meeting -->
<div class="flex items-center gap-2">
    <Button href="/meetings/create" size="sm">
        <Plus class="h-4 w-4" />
        New Meeting
    </Button>
    <Button variant="outline" size="sm" onclick={() => (showModal = true)}>
        <LogIn class="h-4 w-4" />
        Join Meeting
    </Button>
</div>
