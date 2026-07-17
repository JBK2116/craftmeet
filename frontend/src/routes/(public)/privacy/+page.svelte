<script lang="ts">
    import { onMount } from 'svelte';

    // TOC section navigation
    const sections = [
        { id: 'summary', title: 'Summary of Key Points' },
        { id: 'what-we-collect', title: '1. What Information Do We Collect?' },
        { id: 'how-we-process', title: '2. How Do We Process Your Information?' },
        { id: 'legal-bases', title: '3. What Legal Bases Do We Rely On?' },
        { id: 'sharing', title: '4. Sharing Your Personal Information' },
        { id: 'third-party', title: '5. Third-Party Websites' },
        { id: 'tracking', title: '6. Tracking Technologies' },
        { id: 'social-logins', title: '7. How We Use Google Data' },
        { id: 'international', title: '8. International Transfers' },
        { id: 'retention', title: '9. Data Retention' },
        { id: 'security', title: '10. Security' },
        { id: 'minors', title: '11. Minors' },
        { id: 'rights', title: '12. Your Privacy Rights' },
        { id: 'contact', title: '13. Contact Us' },
    ];

    // Active section tracking
    let activeSection = $state('');
    onMount(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        activeSection = entry.target.id;
                    } else if (activeSection === entry.target.id) {
                        activeSection = '';
                    }
                });
            },
            { rootMargin: '-20% 0px -80% 0px' },
        );

        sections.forEach((section) => {
            const el = document.getElementById(section.id);
            if (el) observer.observe(el);
        });
        return () => observer.disconnect();
    });
</script>

<svelte:head>
    <style>
        html {
            scroll-behavior: smooth;
        }
    </style>
</svelte:head>

<main class="relative min-h-screen bg-background text-foreground">
    <!-- Decorative background glow utilizing token safe opacity variables -->
    <div class="pointer-events-none absolute inset-0 flex justify-center overflow-hidden">
        <div class="h-[800px] w-[800px] -translate-y-1/2 rounded-full bg-primary/5 blur-3xl"></div>
    </div>

    <div class="mx-auto flex max-w-7xl flex-col gap-12 px-6 py-24 lg:flex-row lg:px-8">
        <!-- Sidebar Navigation -->
        <aside class="hidden w-64 shrink-0 lg:block">
            <div class="sticky top-24 flex flex-col gap-1">
                <p class="mb-3 text-xs uppercase tracking-widest text-muted-foreground/60">
                    Contents
                </p>
                {#each sections as section}
                    <a
                        href="#{section.id}"
                        class="border-l py-1 pl-4 text-sm transition-all duration-200
                            {activeSection === section.id
                            ? 'border-foreground text-foreground font-medium'
                            : 'border-border text-muted-foreground hover:border-muted-foreground/60 hover:text-foreground'}"
                    >
                        {section.title}
                    </a>
                {/each}
            </div>
        </aside>

        <!-- Document Content -->
        <article
            class="prose prose-neutral dark:prose-invert max-w-3xl
                   prose-p:text-muted-foreground prose-headings:text-foreground prose-a:text-foreground prose-a:underline-offset-4 hover:prose-a:text-muted-foreground
                   [&_h2]:scroll-mt-24 [&_h3]:scroll-mt-24 [&_hr]:border-border [&_blockquote]:border-border"
        >
            <!-- NOTE: Update "Last updated" date below every time this notice is modified -->
            <h1>Privacy Notice</h1>
            <p class="text-sm text-muted-foreground/70">Last updated: July 17, 2026</p>

            <p>
                This privacy notice for <strong>Craftmeet</strong>
                describes how and why we might collect, store, use, and/or share your information when
                you use our services, such as when you:
            </p>
            <ul>
                <li>
                    Visit our website at <a href="https://craftmeet.live">https://craftmeet.live</a
                    >, or any website of ours that links to this privacy notice.
                </li>
                <li>
                    Engage with us in other related ways including any sales, marketing, or events.
                </li>
            </ul>
            <p>
                Questions or concerns? Reading this privacy notice will help you understand your
                privacy rights and choices. If you do not agree with our policies and practices,
                please do not use our Services. If you still have any questions or concerns, please
                contact us at
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a>.
            </p>

            <hr />

            <h2 id="summary">Summary of Key Points</h2>
            <blockquote>
                <p>
                    <strong>In Short:</strong> This summary provides key points from our privacy notice.
                    You can find out more details about any of these topics by navigating to the relevant
                    sections below.
                </p>
            </blockquote>
            <ul>
                <li>
                    <strong>What personal information do we process?</strong> When you visit, use, or
                    navigate our Services, we may process personal information depending on how you interact
                    with Craftmeet, the choices you make, and the features you use (e.g., OAuth data,
                    meeting responses).
                </li>
                <li>
                    <strong>Do we process any sensitive personal information?</strong> We do not intentionally
                    process sensitive personal information unless you voluntarily submit such information
                    within a live meeting session.
                </li>
                <li>
                    <strong>Do you receive any information from third parties?</strong> We receive basic
                    profile information when you authenticate via Google.
                </li>
                <li>
                    <strong>How do you process my information?</strong> We process your information to
                    provide, improve, and administer our Services, communicate with you, and utilize external
                    AI exclusively for generating meeting transcript summaries. We do not sell your data.
                </li>
                <li>
                    <strong
                        >In what situations and with which types of parties do we share personal
                        information?</strong
                    >
                    We share information with specific service providers (e.g., OpenAI for meeting summaries,
                    DigitalOcean for hosting) purely to facilitate the Service.
                </li>
                <li>
                    <strong>How do we keep your information safe?</strong> We employ strict organizational
                    and technical processes to protect your information.
                </li>
            </ul>

            <h2 id="what-we-collect">1. What Information Do We Collect?</h2>
            <h3>Personal Information Provided by You</h3>
            <p>
                The personal information that we collect depends on the context of your interactions
                with us and the Services. We collect:
            </p>
            <ul>
                <li>
                    <strong>Account Data:</strong> Names, email addresses, and avatar URLs provided via
                    OAuth.
                </li>
                <li>
                    <strong>Meeting Data:</strong> Meeting titles, descriptions, and structural configurations.
                </li>
                <li>
                    <strong>Participant Data:</strong> Anonymous session tokens, submitted responses,
                    and chat messages generated during a live meeting.
                </li>
            </ul>

            <h3>Information Automatically Collected</h3>
            <p>
                We automatically collect log and usage data (IP addresses, browser type, diagnostic
                data) and device data primarily to maintain the security and operation of our
                Services.
            </p>

            <h2 id="how-we-process">2. How Do We Process Your Information?</h2>
            <p>We process your personal information for a variety of reasons, including:</p>
            <ul>
                <li>
                    <strong>To facilitate account creation and authentication:</strong> Managing your
                    host account securely.
                </li>
                <li>
                    <strong>To deliver services:</strong> Broadcasting real-time event states and storing
                    meeting session data.
                </li>
                <li>
                    <strong>To generate meeting summaries:</strong> We securely transmit meeting
                    transcripts to our AI provider (OpenAI) strictly for the purpose of generating
                    structured PDF summaries.
                    <strong
                        >We do not permit our AI providers to use your meeting data to train their
                        models.</strong
                    >
                </li>
                <li>
                    <strong>To protect our Services:</strong> Monitoring for fraud and ensuring infrastructure
                    security.
                </li>
            </ul>

            <h2 id="legal-bases">3. What Legal Bases Do We Rely On To Process Your Information?</h2>
            <p>
                <strong>If you are located in Canada:</strong> We may process your information if
                you have given us specific permission (express consent) to use your personal
                information for a specific purpose, or in situations where your permission can be
                inferred (implied consent). We abide by the Personal Information Protection and
                Electronic Documents Act (PIPEDA). If you are a resident of Quebec, we additionally
                acknowledge Quebec's Law 25 (Act respecting the protection of personal information
                in the private sector). We use automated AI processing solely to generate meeting
                summaries, as disclosed in this notice. Our designated Privacy Officer can be
                reached at
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a>.
            </p>
            <p>
                <strong>If you are located in the EU or UK:</strong> We rely on Consent, Performance of
                a Contract, and Legitimate Interests to process your data.
            </p>

            <h2 id="sharing">4. When and With Whom Do We Share Your Personal Information?</h2>
            <p>
                We do not sell your data. We only share information with specific third-party
                infrastructure providers to run the Service:
            </p>
            <ul>
                <li>
                    <strong>Artificial Intelligence Services:</strong> OpenAI (strictly for processing
                    meeting transcripts into summaries; under OpenAI's API data usage policy, your data
                    is not used for model training).
                </li>
                <li>
                    <strong>Cloud Computing & Database Services:</strong> DigitalOcean (for hosting).
                </li>
                <li><strong>User Account Authentication:</strong> Google (for OAuth).</li>
            </ul>
            <p>
                <strong>Other Users:</strong> When you participate in a live Craftmeet session, your submitted
                ideas, votes, and chat messages are visible to the host and other participants in the
                room.
            </p>

            <h2 id="third-party">5. What Is Our Stance on Third-Party Websites?</h2>
            <p>
                Our Services may contain links to third-party websites. We cannot guarantee the
                safety and privacy of data you provide to any third parties once you leave our
                platform.
            </p>

            <h2 id="tracking">6. Do We Use Cookies and Other Tracking Technologies?</h2>
            <p>
                We use a single HTTP-only cookie strictly for authentication purposes to identify
                you as a logged-in host while you use the application. This cookie contains no
                personally identifiable information beyond a secure session token, expires after 1
                day of inactivity, and is cleared on logout. We do not use tracking cookies,
                analytics cookies, or any cookies for third-party advertising.
            </p>

            <h2 id="social-logins">7. How We Use Google Data</h2>
            <p>
                Craftmeet uses <strong>Sign in with Google</strong> as an authentication method for host
                accounts. When you sign in with Google, we request access to the following scopes:
            </p>
            <ul>
                <li>
                    <strong>openid</strong> — to verify your Google identity and associate it with your
                    Craftmeet account.
                </li>
                <li>
                    <strong>profile</strong> — to retrieve your Google display name and profile picture
                    for your Craftmeet account.
                </li>
                <li>
                    <strong>email</strong> — to retrieve your email address for account identification,
                    communication, and support purposes.
                </li>
            </ul>
            <p>
                We use this information <strong>solely</strong> to create and manage your Craftmeet
                account. We do not access your Google Drive, Calendar, Contacts, or any other Google
                service data. We do not share your Google account information with third parties.
                You can revoke Craftmeet's access to your Google account at any time through your
                <a href="https://myaccount.google.com/permissions">Google Account permissions</a>
                page.
            </p>

            <h2 id="international">8. Is Your Information Transferred Internationally?</h2>
            <p>
                Our application servers are hosted by DigitalOcean in New York City, United States.
                By using Craftmeet, your data is stored and processed in the United States. We have
                selected DigitalOcean as our infrastructure provider based on their security
                certifications and data protection standards.
            </p>
            <p>
                Additionally, meeting transcript data is transmitted to OpenAI for processing, also
                in the United States. Under OpenAI's API data usage policy, your data is not used
                for model training.
            </p>

            <h2 id="retention">9. How Long Do We Keep Your Information?</h2>
            <p>
                We keep your information for as long as necessary to fulfill the purposes outlined
                in this privacy notice unless otherwise required by law. Account data is retained
                until you choose to delete your account. Meeting data is retained until you delete
                the specific meeting.
            </p>
            <p>
                AI-generated meeting export PDFs are automatically and permanently deleted 24 hours
                after creation. It is the host's responsibility to download and retain any export
                they wish to keep.
            </p>

            <h2 id="security">10. How Do We Keep Your Information Safe?</h2>
            <p>
                We have implemented technical security measures designed to protect your personal
                information, including TLS encryption, stateless sessions, and secure database
                environments. However, no electronic transmission over the internet can be
                guaranteed to be 100% secure.
            </p>

            <h2 id="minors">11. Do We Collect Information From Minors?</h2>
            <p>
                We do not knowingly collect data from or market to children under 18 years of age.
                By using the Services, you represent that you are at least 18 or that you are the
                parent or guardian of such a minor and consent to such minor dependent's use of the
                Services.
            </p>

            <h2 id="rights">12. What Are Your Privacy Rights?</h2>
            <p>
                If you are located in Canada, the EEA, or the UK, you have certain rights under
                applicable data protection laws, including the right to request access to,
                rectification of, or erasure of your personal information. To make such a request,
                please contact us at <a href="mailto:support@craftmeet.live"
                    >support@craftmeet.live</a
                >. We will respond to all legitimate requests within 30 days. Occasionally it may
                take us longer if your request is particularly complex or you have made a number of
                requests, in which case we will notify you and keep you updated.
            </p>

            <h2 id="contact">13. How Can You Contact Us About This Notice?</h2>
            <p>
                If you have questions or comments about this notice, or wish to exercise any of your
                privacy rights, you may contact our Privacy Officer by email at
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a>. We will respond
                to all requests within 30 days.
            </p>
            <address class="not-italic text-muted-foreground">
                <strong>Craftmeet</strong><br />
                Privacy Officer:
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a><br />
                United States (DigitalOcean NYC)
            </address>
        </article>
    </div>
</main>
