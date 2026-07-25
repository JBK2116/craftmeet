<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import * as Sheet from '$lib/components/ui/sheet';
    import type { ChatMessage } from '$lib/types/websocket';
    import { formatCreatedAtChat } from '$lib/utils/time';
    import { Crown, MessageCircle, Send } from '@lucide/svelte';

    let {
        open = $bindable(false),
        chats = [] as ChatMessage[],
        onsend,
    }: { open?: boolean; chats?: ChatMessage[]; onsend?: (message: string) => void } = $props();

    let messageText = $state('');
    let scrollEl = $state<HTMLDivElement>();

    function handleSend() {
        const trimmed = messageText.trim();
        if (!trimmed || !onsend) return;
        onsend(trimmed);
        messageText = '';
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    $effect(() => {
        // Scroll to bottom when new messages arrive
        if (scrollEl && chats.length > 0) {
            scrollEl.scrollTop = scrollEl.scrollHeight;
        }
    });
</script>

<Sheet.Root bind:open>
    <Sheet.Trigger>
        {#snippet child({ props })}
            <Button variant="ghost" size="icon" class="relative" aria-label="Open chat" {...props}>
                <MessageCircle class="size-5" />
                {#if chats.length > 0}
                    <span
                        class="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground"
                    >
                        {chats.length}
                    </span>
                {/if}
            </Button>
        {/snippet}
    </Sheet.Trigger>

    <Sheet.Content side="right" class="flex h-full flex-col sm:max-w-sm">
        <Sheet.Header>
            <Sheet.Title class="flex items-center gap-2">
                <MessageCircle class="size-4" />
                Chat
            </Sheet.Title>
        </Sheet.Header>

        <!-- Messages -->
        <div bind:this={scrollEl} class="flex-1 overflow-y-auto px-4 py-2">
            {#if chats.length === 0}
                <div class="flex flex-col items-center gap-2 py-12 text-center">
                    <MessageCircle class="size-8 text-muted-foreground/40" />
                    <p class="text-sm text-muted-foreground">No messages yet</p>
                    <p class="text-xs text-muted-foreground/60">Chat messages will appear here</p>
                </div>
            {:else}
                <div class="space-y-3">
                    {#each chats as msg (msg.u_id + msg.created_at)}
                        <div class="rounded-lg border border-border bg-muted/30 px-3 py-2">
                            <div class="mb-1 flex items-center gap-1.5">
                                <span class="text-xs font-semibold text-foreground">
                                    {msg.name}
                                </span>
                                {#if msg.is_host}
                                    <span
                                        class="flex items-center gap-0.5 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600"
                                        title="Host"
                                    >
                                        <Crown class="size-3" />
                                        Host
                                    </span>
                                {/if}
                                <span class="ml-auto text-[10px] text-muted-foreground">
                                    {formatCreatedAtChat(msg.created_at)}
                                </span>
                            </div>
                            <p class="text-sm text-foreground break-words">
                                {msg.message}
                            </p>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>

        <!-- Input -->
        {#if onsend}
            <div class="border-t border-border px-4 py-3">
                <div class="flex items-center gap-2">
                    <Input
                        bind:value={messageText}
                        placeholder="Type a message..."
                        onkeydown={handleKeydown}
                        class="flex-1"
                    />
                    <Button
                        size="icon-sm"
                        variant="default"
                        onclick={handleSend}
                        disabled={!messageText.trim()}
                        aria-label="Send message"
                    >
                        <Send class="size-4" />
                    </Button>
                </div>
            </div>
        {/if}
    </Sheet.Content>
</Sheet.Root>
