import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Terms and Conditions - Craftmeet',
            description: "Craftmeet's terms and conditions of service.",
            url: 'https://craftmeet.live/terms',
            ogTitle: 'Craftmeet - Terms and Conditions',
        } satisfies PageMeta,
    };
};
