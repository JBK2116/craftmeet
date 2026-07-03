import { apiFetch } from '$lib/api/auth';
import { user } from '$lib/stores/stores';
import { AuthError } from '$lib/types/errors';
import type { MeetingIn } from '$lib/types/meeting';
import type { PageMeta } from '$lib/types/meta';
import { error, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
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
    if (meeting.user_id !== get(user)?.id) {
        throw error(401, 'You are not the host of this meeting');
    }
    return {
        meta: {
            title: `Host: ${meeting.title} - Craftmeet`,
            description: `Host your meeting "${meeting.title}" and guide participants through each question in real time.`,
            url: `https://craftmeet.live/meetings/${slug}/host`,
            ogTitle: `Host: ${meeting.title} - Craftmeet`,
        } satisfies PageMeta,
        meeting,
    };
};
