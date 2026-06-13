/**
 * SEO metadata for a route, returned from a `+page.ts` `load` as `{ meta }` and
 * rendered centrally by the root `+layout.svelte`. Keeping this in one place lets
 * every page describe itself with plain data instead of its own `<svelte:head>`.
 */
export interface PageMeta {
    /** Full document title, rendered verbatim (e.g. "Sign In - Craftmeet"). */
    title: string;
    /** Meta description; also used as the default Open Graph description. */
    description: string;
    /** Canonical URL for the page. Drives both `<link rel="canonical">` and `og:url`. */
    url?: string;
    /** Open Graph title, when it should differ from `title`. Defaults to `title`. */
    ogTitle?: string;
    /** Open Graph image path. Defaults to `/og-image.png`. */
    ogImage?: string;
}
