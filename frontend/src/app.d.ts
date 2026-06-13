// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { PageMeta } from '$lib/types/meta';

declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        interface PageData {
            /** SEO metadata rendered by the root layout. See `$lib/types/meta`. */
            meta?: PageMeta;
        }
        // interface PageState {}
        // interface Platform {}
    }
}

export {};
