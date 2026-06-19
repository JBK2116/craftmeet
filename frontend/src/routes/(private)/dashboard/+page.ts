import { apiFetch } from '$lib/api/auth';
import { AuthError } from '$lib/types/errors';
import type { MeetingIn } from '$lib/types/meeting';
import type { PageMeta } from '$lib/types/meta';
import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// This page had no <svelte:head>, so the metadata below is a sensible default
// derived from the route ("dashboard").
export const load: PageLoad = async ({ fetch }) => {
    // load the starting meetings from the backend
    const url = `/api/v1/meeting`;
    const opts: RequestInit = { method: 'GET', credentials: 'include' };
    let meetings: MeetingIn[] = [];
    try {
        const res = await apiFetch(url, opts, fetch);
        if (!res.ok) {
            throw new Error(`Failed to load meetings: ${res.status}`);
        }
        const body = await res.json();
        meetings = body as MeetingIn[];
    } catch (err: any) {
        if (err instanceof AuthError) {
            throw redirect(302, '/login');
        }
        throw err;
    }
    // return the page load data
    return {
        meta: {
            title: 'Dashboard - Craftmeet',
            description:
                'Manage your meetings, monitor live sessions, and review AI-generated summaries from your Craftmeet dashboard.',
            url: 'https://craftmeet.com/dashboard',
            ogTitle: 'Craftmeet - Dashboard',
        } satisfies PageMeta,
        meetings: meetings,
    };
};
