import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Craftmeet — Structured, Idea-Driven Meetings',
            description:
                'Craftmeet is a real-time meeting platform for hosting structured, idea-driven sessions with flexible question formats, live collaboration, and AI-generated summaries.',
            url: 'https://craftmeet.live',
            ogTitle: 'Craftmeet — Structured, Idea-Driven Meetings',
        } satisfies PageMeta,
    };
};
