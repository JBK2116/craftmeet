import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Pricing - Craftmeet',
            description: "Craftmeet's pricing plans and features.",
            url: 'https://craftmeet.com/pricing',
            ogTitle: 'Craftmeet - Pricing',
        } satisfies PageMeta,
    };
};
