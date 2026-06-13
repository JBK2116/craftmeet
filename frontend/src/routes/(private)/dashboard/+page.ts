import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

// This page had no <svelte:head>, so the metadata below is a sensible default
// derived from the route ("dashboard").
export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Dashboard - Craftmeet',
            description:
                'Manage your meetings, monitor live sessions, and review AI-generated summaries from your Craftmeet dashboard.',
            url: 'https://craftmeet.com/dashboard',
            ogTitle: 'Craftmeet - Dashboard',
        } satisfies PageMeta,
    };
};
