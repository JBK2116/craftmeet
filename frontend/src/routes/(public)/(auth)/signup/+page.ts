import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Sign Up - Craftmeet',
            description:
                'Create your Craftmeet account and start hosting real-time structured meetings with AI-generated summaries.',
            url: 'https://craftmeet.com/signup',
            ogTitle: 'Craftmeet - Sign Up',
        } satisfies PageMeta,
    };
};
