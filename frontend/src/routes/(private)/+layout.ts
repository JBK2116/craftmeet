import { browser } from '$app/environment';
import { user } from '$lib/stores/stores';
import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';

export async function load({ parent }) {
    if (!browser) {
        return;
    }
    // ensure that the root layout.ts runs first
    // this allows it to check the /me endpoint and set the user store depending the user's auth status
    await parent();
    // if the user is not authenticated, redirect them to the login page
    if (!get(user)) {
        throw redirect(302, '/login');
    }
}
