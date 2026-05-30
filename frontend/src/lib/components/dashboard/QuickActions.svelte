<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { LogIn, Plus } from '@lucide/svelte';
</script>

<!-- quick actions for create meeting and join meeting -->
<div class="flex items-center gap-2">
    <Button href="/meetings/create" size="sm">
        <Plus class="h-4 w-4" />
        New Meeting
    </Button>
    <Button href="/join" variant="outline" size="sm">
        <LogIn class="h-4 w-4" />
        Join Meeting
    </Button>
</div>
