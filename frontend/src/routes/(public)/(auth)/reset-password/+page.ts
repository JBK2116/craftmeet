import type { PageMeta } from '$lib/types/meta';

import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Reset Password - Craftmeet',
            description:
                'Reset your Craftmeet account password and regain access to your meetings.',
            url: 'https://craftmeet.com/reset-password',
            ogTitle: 'Craftmeet - Reset Password',
        } satisfies PageMeta,
    };
};
