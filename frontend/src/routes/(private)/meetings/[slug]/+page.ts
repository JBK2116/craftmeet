import { apiFetch } from '$lib/api/auth';
import { AuthError } from '$lib/types/errors';
import type { MeetingIn } from '$lib/types/meeting';
import type { PageMeta } from '$lib/types/meta';
import { error, redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const prerender = false;

export const load: PageLoad = async ({ fetch, params }) => {
    // load the starting meetings from the backend
    const slug = params.slug;
    const url = `/api/v1/meetings/${slug}`;
    const opts: RequestInit = { method: 'GET', credentials: 'include' };
    let meeting: MeetingIn;
    try {
        const res = await apiFetch(url, opts, fetch);
        if (!res.ok) {
            if (res.status === 404) {
                throw error(404, 'Meeting not found');
            }
            if (res.status === 500) {
                throw error(500, 'Server Error');
            }
            throw new Error(`Failed to load meetings: ${res.status}`);
        }
        const body = await res.json();
        meeting = body as MeetingIn;
    } catch (err: any) {
        if (err instanceof AuthError) {
            throw redirect(302, '/login');
        }
        throw err;
    }
    // return the page load data
    return {
        meta: {
            title: `${meeting.title} - Craftmeet`,
            description: `Edit and manage ${meeting.title}, review questions, and control your meeting settings.`,
            url: `https://craftmeet.live/meetings/${slug}`,
            ogTitle: `${meeting.title} - Craftmeet`,
        } satisfies PageMeta,
        meeting: meeting,
    };
};
