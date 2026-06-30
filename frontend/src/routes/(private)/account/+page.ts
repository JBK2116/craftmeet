import { apiFetch } from '$lib/api/auth';
import { AuthError } from '$lib/types/errors';
import type { PageMeta } from '$lib/types/meta';
import type { User } from '$lib/types/user';
import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    const url = `/api/v1/auth/me`;
    const opts: RequestInit = { method: 'GET', credentials: 'include' };
    let user: User | null = null;
    try {
        const res = await apiFetch(url, opts, fetch);
        if (!res.ok) {
            throw new Error(`Failed to load user: ${res.status}`);
        }
        user = (await res.json()) as User;
    } catch (err: any) {
        if (err instanceof AuthError) {
            throw redirect(302, '/login');
        }
        throw err;
    }

    return {
        meta: {
            title: 'Account - Craftmeet',
            description: 'Manage your account settings, profile, and preferences on Craftmeet.',
            url: 'https://craftmeet.live/account',
            ogTitle: 'Craftmeet - Account Settings',
        } satisfies PageMeta,
        user,
    };
};
