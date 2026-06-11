import { browser } from '$app/environment';
import { refreshTokens } from '$lib/api/auth.js';
import { user } from '$lib/stores/stores';

export const csr = true; // Enable client side rendering
export const ssr = false; // Disable server side rendering
export const prerender = false; // Disable prerendering

export async function load({ fetch }) {
    // this function should only run when the user is in the browser
    if (!browser) {
        return;
    }
    const url = `/api/v1/auth/me`;
    let response = await fetch(url, { method: 'GET', credentials: 'include' });
    if (response.status === 401) {
        // access token failed validation and will need to be refreshed
        const isRefreshed = await refreshTokens(fetch);
        if (isRefreshed) {
            response = await fetch(url, { method: 'GET', credentials: 'include' });
        }
    }
    if (!response.ok) {
        user.set(null);
        return;
    }
    // the backend will send back the user's object response
    const body = await response.json();
    user.set(body);
    return;
}
