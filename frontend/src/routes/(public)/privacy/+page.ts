import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Privacy Policy - Craftmeet',
            description: "Craftmeet's privacy notice and data processing policies.",
            url: 'https://craftmeet.com/privacy',
            ogTitle: 'Craftmeet - Privacy Policy',
        } satisfies PageMeta,
    };
};
