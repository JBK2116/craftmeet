<script lang="ts">
    let {
        open = $bindable(false),
        title,
        message,
    }: { open?: boolean; title: string; message: string } = $props();

    function closeModal(): void {
        open = false;
    }

    function handleModalKeydown(e: KeyboardEvent): void {
        if (e.key === 'Escape') closeModal();
    }
</script>

<svelte:window onkeydown={open ? handleModalKeydown : undefined} />

{#if open}
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 backdrop-blur-sm"
        onclick={closeModal}
        onkeydown={handleModalKeydown}
        role="presentation"
    >
        <div
            class="w-full max-w-[380px] rounded-2xl border border-border bg-card p-8 shadow-overlay"
            onkeydown={(e) => e.stopPropagation()}
            onclick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            tabindex="-1"
        >
            <div class="mb-5 flex justify-center">
                <div class="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-6 w-6 text-primary"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.75"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                        />
                    </svg>
                </div>
            </div>

            <h2
                id="modal-title"
                class="mb-1.5 text-center text-subheading font-semibold tracking-tight text-foreground"
            >
                {title}
            </h2>
            <p class="mb-6 text-center text-small text-muted-foreground">
                {message}
            </p>

            <button
                onclick={closeModal}
                class="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-small font-medium text-primary-foreground transition
                    hover:bg-primary/90 active:scale-[0.98]"
            >
                Got it
            </button>
        </div>
    </div>
{/if}
