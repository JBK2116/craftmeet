import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Verify Email - Craftmeet',
            description: 'Confirming your Craftmeet email address.',
            url: 'https://craftmeet.com/verify-email',
            ogTitle: 'Craftmeet - Verify Email',
        } satisfies PageMeta,
    };
};
