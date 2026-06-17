import { goto } from '$app/navigation';
import { user } from '$lib/stores/stores';

/**
 * Custom error class representing an authentication failure.
 */
class AuthError extends Error {
    constructor() {
        super('AUTH_FAILED');
    }
}

/**
 * Refreshes the authentication tokens by making a POST request to the refresh endpoint.
 * Uses credentials to include cookies in the request.
 *
 * @param {typeof fetch} [customFetch=fetch] Optional fetch wrapper to use.
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
 * @note The caller is responsible for clearing local user state (e.g., user store) after calling this.
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

/**
 * Makes an authenticated fetch request, automatically refreshing tokens on a 401 response.
 * If the token refresh fails, the user is logged out, the user store is cleared,
 * and the user is redirected to /login.
 *
 * @param {string} url - The URL to fetch.
 * @param {RequestInit} opts - Standard fetch options (method, headers, body, etc.).
 * @returns {Promise<Response | undefined>} The fetch Response on success, or `undefined` if the user was redirected due to an unrecoverable auth failure.
 * @throws {Error} Rethrows network or unexpected errors (non-auth failures).
 */
export async function apiFetch(url: string, opts: RequestInit): Promise<Response | undefined> {
    try {
        let res = await fetch(url, opts);
        if (res.status === 401) {
            const ok = await refreshTokens();
            if (!ok) {
                throw new AuthError();
            }
            res = await fetch(url, opts);
            return res;
        }
        return res;
    } catch (err: any) {
        if (err instanceof AuthError) {
            await logout();
            user.set(null);
            goto('/login');
            return;
        } else {
            throw err;
        }
    }
}
