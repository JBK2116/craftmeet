import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Contact - Craftmeet',
            description:
                'Get in touch with the Craftmeet team. Reach us directly by email at support@craftmeet.com.',
            url: 'https://craftmeet.com/contact',
            ogTitle: 'Craftmeet - Contact',
        } satisfies PageMeta,
    };
};
