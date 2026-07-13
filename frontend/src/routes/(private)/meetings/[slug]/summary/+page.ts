import { apiFetch } from '$lib/api/auth';
import { user } from '$lib/stores/stores';
import { AuthError } from '$lib/types/errors';
import type { MeetingIn } from '$lib/types/meeting';
import type { PageMeta } from '$lib/types/meta';
import { error, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
    // load the meeting data from the backend
    const slug = params.slug;
    const url = `/api/v1/meetings/${slug}`;
    const opts: RequestInit = { method: 'GET', credentials: 'include' };
    let meeting: MeetingIn;
    try {
        const res = await apiFetch(url, opts, fetch);
        if (!res.ok) {
            if (res.status === 404) throw error(404, 'Meeting not found');
            if (res.status === 500) throw error(500, 'Server Error');
            throw new Error(`Failed to load meeting: ${res.status}`);
        }
        meeting = (await res.json()) as MeetingIn;
    } catch (err: any) {
        if (err instanceof AuthError) throw redirect(302, '/login');
        throw err;
    }
    // only the meeting host may view the summary
    if (meeting.user_id !== get(user)?.id) {
        throw error(403, 'You are not the host of this meeting');
    }
    // return the page load data
    return {
        meta: {
            title: `Summary: ${meeting.title} - Craftmeet`,
            description: `Review stats, responses, and an AI-generated summary for "${meeting.title}".`,
            url: `https://craftmeet.live/meetings/${slug}/summary`,
            ogTitle: `Summary: ${meeting.title} - Craftmeet`,
        } satisfies PageMeta,
        meeting,
    };
};
