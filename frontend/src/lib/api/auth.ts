import { user } from '$lib/stores/stores';
import { get } from 'svelte/store';

/**
 * Refreshes the authentication tokens by making a POST request to the refresh endpoint.
 * Uses credentials to include cookies in the request.
 *
 * @param [customFetch=fetch] Optional fetch wrapper to use
 * @returns {Promise<boolean>} True if the token refresh was successful, false otherwise.
 */
export async function refreshTokens(customFetch: typeof fetch = fetch): Promise<boolean> {
    try {
        const url = `/api/v1/auth/refresh`;
        const headers = { 'Content-Type': 'application/json' };
        const response = await customFetch(url, {
            method: 'POST',
            credentials: 'include',
            headers,
        });
        return response.ok;
    } catch (err: any) {
        return false;
    }
}

/**
 * Logs out the user by making a POST request to the logout endpoint.
 * Uses credentials to include cookies in the request.
 *
 * @note Regardless of any failures, it is best practice to still clear the user's local state.
 * The backend will handle fixing their state.  
 * @returns {Promise<boolean>} True if the logout request was successful, false otherwise.
 */
export async function logout(): Promise<boolean> {
    try {
        const url = `/api/v1/auth/logout`;
        const headers = { 'Content-Type': 'application/json' };
        const response = await fetch(url, { method: 'POST', credentials: 'include', headers });
        return response.ok;
    } catch (err: any) {
        return false;
    }
}
