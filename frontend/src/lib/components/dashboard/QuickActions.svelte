<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { LogIn, Plus } from '@lucide/svelte';
</script>

<!-- quick actions for create meeting and join meeting -->
<div class="flex flex-col gap-3 sm:flex-row">
    <Button href="/meetings/create" class="w-full sm:w-auto">
        <Plus class="h-4 w-4" />
        New Meeting
    </Button>
    <Button href="/join" variant="ghost" class="w-full sm:w-auto">
        <LogIn class="h-4 w-4" />
        Join Meeting
    </Button>
</div>
