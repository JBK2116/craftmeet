import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Sign In - Craftmeet',
            description:
                'Sign in to your Craftmeet account and continue hosting real-time structured meetings with AI-generated summaries.',
            url: 'https://craftmeet.com/login',
            ogTitle: 'Craftmeet - Sign In',
        } satisfies PageMeta,
    };
};
