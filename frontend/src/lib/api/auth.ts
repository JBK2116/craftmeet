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
        const response = await fetch(url, { method: 'POST', credentials: 'include' });
        return response.ok;
    } catch (err: any) {
        return false;
    }
}
