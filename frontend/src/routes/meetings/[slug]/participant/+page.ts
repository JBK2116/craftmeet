import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = ({ params }) => {
    return {
        meta: {
            title: `Meeting ${params.slug} - Craftmeet`,
            description: 'Join a live meeting session and share your responses in real time.',
        } satisfies PageMeta,
    };
};
