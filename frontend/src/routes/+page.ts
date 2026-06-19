import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Craftmeet',
            description:
                'Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces.',
            url: 'https://craftmeet.live',
            ogTitle: 'Craftmeet - Structured, Idea-Driven Meetings',
        } satisfies PageMeta,
    };
};
