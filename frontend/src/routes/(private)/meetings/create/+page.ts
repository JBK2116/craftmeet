import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    return {
        meta: {
            title: 'Create Meeting - Craftmeet',
            description: 'Create a real-time structured meeting with flexible question formats',
            url: 'https://craftmeet.live',
            ogTitle: 'Craftmeet - Create Meeting',
        },
    };
};
