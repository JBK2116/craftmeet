<script>
    import Navbar from '$lib/components/Navbar.svelte';
</script>

<!-- Document Head -->
<svelte:head>
    <title>Craftmeet</title>
    <meta
        name="description"
        content="Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces."
    />
    <!-- TODO: Ensure that the og URL here matches the actual domain URL. -->
    <link rel="canonical" href="https://craftmeet.com" />
    <!-- OG Properties -->
    <meta property="og:title" content="Craftmeet - Structured, Idea-Driven Meetings" />
    <meta
        property="og:description"
        content="Host real-time structured meetings with flexible question formats, live collaboration, and AI-generated summaries of every idea your room produces."
    />
    <!-- TODO: Ensure that the og URL here matches the actual domain URL. -->
    <meta property="og:url" content="https://craftmeet.com" />
    <meta property="og:type" content="website" />
    <!-- TODO: Ensure that the image here is replaced by the site's actual UI image later. -->
    <meta property="og:image" content="/og-image.png" />
</svelte:head>
<Navbar></Navbar>
