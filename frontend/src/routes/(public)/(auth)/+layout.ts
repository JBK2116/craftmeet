import { browser } from '$app/environment';
import { user } from '$lib/stores/stores';
import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';

export async function load() {
    if (!browser) {
        return;
    }
    // if the user is already authenticated, redirect them to the dashboard page
    if (get(user)) {
        redirect(302, '/dashboard');
    }
}
