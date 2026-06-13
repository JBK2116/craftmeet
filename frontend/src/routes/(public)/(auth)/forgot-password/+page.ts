import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Forgot Password - Craftmeet',
            description: 'Reset your Craftmeet account password.',
            url: 'https://craftmeet.com/forgot-password',
            ogTitle: 'Craftmeet - Forgot Password',
        } satisfies PageMeta,
    };
};
