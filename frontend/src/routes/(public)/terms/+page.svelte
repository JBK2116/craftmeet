<script lang="ts">
    import { onMount } from 'svelte';

    const sections = [
        { id: 'our-services', title: '1. Our Services' },
        { id: 'intellectual-property', title: '2. Intellectual Property' },
        { id: 'user-representations', title: '3. User Representations' },
        { id: 'user-registration', title: '4. User Registration' },
        { id: 'prohibited-activities', title: '5. Prohibited Activities' },
        { id: 'user-contributions', title: '6. User Generated Contributions' },
        { id: 'contribution-license', title: '7. Contribution License' },
        { id: 'third-party', title: '8. Third-Party Websites' },
        { id: 'services-management', title: '9. Services Management' },
        { id: 'privacy-policy', title: '10. Privacy Policy' },
        { id: 'dmca', title: '11. DMCA' },
        { id: 'term-termination', title: '12. Term & Termination' },
        { id: 'modifications', title: '13. Modifications & Interruptions' },
        { id: 'governing-law', title: '14. Governing Law' },
        { id: 'dispute-resolution', title: '15. Dispute Resolution' },
        { id: 'corrections', title: '16. Corrections' },
        { id: 'disclaimer', title: '17. Disclaimer' },
        { id: 'liability', title: '18. Limitations of Liability' },
        { id: 'indemnification', title: '19. Indemnification' },
        { id: 'user-data', title: '20. User Data' },
        { id: 'electronic-communications', title: '21. Electronic Communications' },
        { id: 'miscellaneous', title: '22. Miscellaneous' },
        { id: 'contact', title: '23. Contact Us' },
    ];

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
    <div class="pointer-events-none absolute inset-0 flex justify-center overflow-hidden">
        <div class="h-[800px] w-[800px] -translate-y-1/2 rounded-full bg-primary/5 blur-3xl"></div>
    </div>

    <div class="mx-auto flex max-w-7xl flex-col gap-12 px-6 py-24 lg:flex-row lg:px-8">
        <aside class="hidden w-64 shrink-0 lg:block">
            <div class="sticky top-24 flex flex-col gap-1">
                <p class="mb-3 text-xs uppercase tracking-widest text-muted-foreground">Contents</p>
                {#each sections as section}
                    <a
                        href="#{section.id}"
                        class="border-l py-1 pl-4 text-sm transition-all duration-200
                            {activeSection === section.id
                            ? 'border-primary text-primary font-medium'
                            : 'border-border text-muted-foreground hover:border-muted hover:text-foreground'}"
                    >
                        {section.title}
                    </a>
                {/each}
            </div>
        </aside>

        <article
            class="prose prose-p:text-muted-foreground prose-headings:text-foreground prose-a:text-primary prose-a:underline-offset-4 hover:prose-a:text-primary/80 max-w-3xl
                    [&_h2]:scroll-mt-24 [&_h3]:scroll-mt-24"
        >
            <!-- NOTE: Update "Last updated" date below every time these terms are modified -->
            <h1>Terms and Conditions</h1>
            <p class="text-sm text-muted-foreground">Last updated: July 17, 2026</p>

            <p>
                These Terms and Conditions constitute a legally binding agreement between you and
                <strong class="text-primary">Craftmeet</strong> governing your access to and use of
                our services at
                <a href="https://craftmeet.live">https://craftmeet.live</a> and any related services that
                link to these terms.
            </p>
            <p>
                By accessing the Services, you confirm that you have read, understood, and agreed to
                be bound by these Terms and Conditions in full. If you do not agree, you must stop
                using the Services immediately.
            </p>
            <p>
                The Services are intended for users who are at least 18 years old. If you are under
                18, you may not use or register for the Services.
            </p>

            <hr class="border-border" />

            <h2 id="our-services">1. Our Services</h2>
            <p>
                Craftmeet is a live meeting facilitation tool that allows hosts to create structured
                sessions with multiple question formats, manage real-time participant responses, and
                generate AI-powered PDF summaries of completed sessions. Participants may join
                sessions without creating an account.
            </p>
            <p>
                The Services are not tailored to comply with industry-specific regulations such as
                HIPAA or FISMA. If your use of the Services would be subject to such laws, you may
                not use the Services.
            </p>
            <p>
                We reserve the right to modify, suspend, or discontinue the Services or any part
                thereof at any time without notice or liability.
            </p>

            <h2 id="intellectual-property">2. Intellectual Property Rights</h2>
            <h3>Our Content</h3>
            <p>
                We own or are licensed to use all intellectual property rights in the Services,
                including all source code, functionality, software, designs, text, graphics, and
                marks. These are protected by copyright, trademark, and other applicable laws. You
                may not copy, reproduce, distribute, sell, or exploit any part of the Services
                without our express prior written permission.
            </p>
            <p>
                Subject to your compliance with these Terms, we grant you a limited, non-exclusive,
                non-transferable, revocable license to access and use the Services solely for your
                internal business or personal facilitation purposes.
            </p>

            <h3>Your Submissions</h3>
            <p>
                If you send us feedback, suggestions, or ideas about the Services directly, you
                agree that we may use them freely without any obligation or compensation to you. For
                content you submit through the Services during live sessions (responses, ideas, chat
                messages), you retain ownership but grant us the rights described in section 7
                (Contribution License) to operate and improve the Services.
            </p>

            <h2 id="user-representations">3. User Representations</h2>
            <p>By using the Services, you represent and warrant that:</p>
            <ul class="text-muted-foreground">
                <li>You are at least 18 years of age.</li>
                <li>
                    Any registration information you provide is accurate, current, and complete.
                </li>
                <li>You have the legal capacity to agree to these Terms.</li>
                <li>You will not access the Services through automated or non-human means.</li>
                <li>You will not use the Services for any illegal or unauthorized purpose.</li>
                <li>Your use of the Services will not violate any applicable law or regulation.</li>
            </ul>
            <p>
                If any information you provide is untrue, inaccurate, or incomplete, we reserve the
                right to suspend or terminate your account and refuse any current or future access
                to the Services.
            </p>

            <h2 id="user-registration">4. User Registration</h2>
            <p>
                Hosts are required to register for an account via Google OAuth or standard email and
                password to access the Services. You are responsible for maintaining the
                confidentiality of your account and for all activity that occurs under it. You agree
                to notify us immediately at
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a> if you suspect any
                unauthorized access to your account.
            </p>
            <p>
                Participants joining a live session do not require an account. A temporary session
                token is issued on join and is valid only for the duration of that session.
            </p>

            <h2 id="prohibited-activities">5. Prohibited Activities</h2>
            <p>
                You may only use the Services for their intended purpose. The following activities
                are strictly prohibited:
            </p>
            <ul class="text-muted-foreground">
                <li>
                    Systematically scraping, harvesting, or collecting data from the Services
                    without our written permission.
                </li>
                <li>Using automated tools, scripts, bots, or spiders to access the Services.</li>
                <li>
                    Circumventing, disabling, or interfering with any security or access control
                    feature of the Services.
                </li>
                <li>Attempting to impersonate another user, host, or participant.</li>
                <li>
                    Submitting false, misleading, defamatory, obscene, or harmful content through
                    any meeting session or chat.
                </li>
                <li>Using the Services to harass, intimidate, or harm any individual.</li>
                <li>
                    Uploading or transmitting viruses, malicious code, or any material that
                    interferes with the operation of the Services.
                </li>
                <li>
                    Using the Services to compete with us or for any unauthorized commercial
                    purpose.
                </li>
                <li>
                    Reverse engineering, decompiling, or disassembling any part of the Services.
                </li>
                <li>Using the Services in any way that violates applicable laws or regulations.</li>
            </ul>

            <h2 id="user-contributions">6. User Generated Contributions</h2>
            <p>
                The Services allow hosts and participants to submit content including meeting
                responses, ideas, votes, ratings, and chat messages (collectively, "Contributions").
                By submitting Contributions, you represent and warrant that:
            </p>
            <ul class="text-muted-foreground">
                <li>
                    Your Contributions are your own and do not infringe the intellectual property
                    rights of any third party.
                </li>
                <li>
                    Your Contributions are not false, misleading, defamatory, obscene, or otherwise
                    harmful.
                </li>
                <li>
                    Your Contributions do not violate any applicable law, regulation, or these
                    Terms.
                </li>
                <li>
                    Your Contributions do not violate the privacy or publicity rights of any third
                    party.
                </li>
            </ul>
            <p>
                You are solely responsible for your Contributions. We reserve the right to remove
                any Contribution at any time if we determine it violates these Terms, without notice
                or liability.
            </p>

            <h2 id="contribution-license">7. Contribution License</h2>
            <p>
                By submitting Contributions through the Services, you grant us a limited,
                non-exclusive license to store, process, and transmit your Contributions solely as
                necessary to operate the Services including broadcasting responses in real time,
                persisting session data, and generating your AI-powered meeting summary.
            </p>
            <p>
                We do not claim ownership over your Contributions. We will not use your
                Contributions for advertising or share them with third parties beyond what is
                described in our <a href="/privacy">Privacy Notice</a>. You retain full ownership of
                everything you submit.
            </p>

            <h2 id="third-party">8. Third-Party Websites</h2>
            <p>
                The Services may contain links to third-party websites. We do not investigate,
                monitor, or endorse any third-party content, and we are not responsible for any harm
                resulting from your access to or use of third-party sites. Once you leave the
                Services, these Terms no longer apply and you should review the applicable terms and
                policies of any site you visit.
            </p>

            <h2 id="services-management">9. Services Management</h2>
            <p>
                We reserve the right, but not the obligation, to monitor the Services for violations
                of these Terms and to take appropriate action, including suspending or terminating
                accounts, removing content, and reporting to law enforcement where necessary. We may
                also limit or disable access to the Services at any time to protect the integrity
                and performance of the platform.
            </p>

            <h2 id="privacy-policy">10. Privacy Policy</h2>
            <p>
                Your use of the Services is also governed by our
                <a href="/privacy">Privacy Notice</a>, which is incorporated into these Terms by
                reference. By using the Services, you consent to the data practices described
                therein. Our servers are hosted in the United States (DigitalOcean, New York City).
                By using the Services, you consent to your data being transferred to and processed
                in the United States.
            </p>

            <h2 id="dmca">11. Digital Millennium Copyright Act (DMCA)</h2>
            <h3>Notifications</h3>
            <p>
                We respect the intellectual property rights of others. If you believe that any
                content available through the Services infringes a copyright you own or control,
                please send a written notification to
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a> that includes:
            </p>
            <ul class="text-muted-foreground">
                <li>
                    Your physical or electronic signature, or that of a person authorized to act on
                    behalf of the copyright owner.
                </li>
                <li>Identification of the copyrighted work you believe has been infringed.</li>
                <li>
                    Identification of the material that is allegedly infringing and enough
                    information for us to locate it.
                </li>
                <li>Your contact information including name, address, and email address.</li>
                <li>
                    A statement that you have a good faith belief the use is not authorized by the
                    copyright owner, its agent, or the law.
                </li>
                <li>
                    A statement, made under penalty of perjury, that the information in your
                    notification is accurate and that you are authorized to act on behalf of the
                    copyright owner.
                </li>
            </ul>

            <h3>Counter Notifications</h3>
            <p>
                If you believe your content was removed by mistake, you may submit a written counter
                notification to <a href="mailto:support@craftmeet.live">support@craftmeet.live</a>
                that includes your name, address, contact information, identification of the removed material
                and its prior location, a statement consenting to jurisdiction of the courts of Ontario,
                Canada, and your physical or electronic signature.
            </p>

            <h2 id="term-termination">12. Term & Termination</h2>
            <p>
                These Terms remain in effect for as long as you use the Services. We reserve the
                right to deny, suspend, or terminate your access to the Services at any time and for
                any reason, including breach of these Terms, without notice or liability.
            </p>
            <p>
                If your account is terminated, you may not re-register under the same or a different
                name without our express permission. Termination does not limit any other rights or
                remedies available to us.
            </p>

            <h2 id="modifications">13. Modifications & Interruptions</h2>
            <p>
                We reserve the right to change, modify, or remove any part of the Services at any
                time without notice. We are not liable for any loss or inconvenience caused by
                unavailability of the Services due to maintenance, hardware or software failures, or
                circumstances beyond our reasonable control. We make no guarantee of uptime or
                uninterrupted access.
            </p>

            <h2 id="governing-law">14. Governing Law</h2>
            <p>
                These Terms and your use of the Services are governed by the laws of the Province of
                Ontario and the federal laws of Canada applicable therein, without regard to
                conflict of law principles. You agree that any legal proceedings arising out of or
                relating to these Terms or the Services shall be brought exclusively in the courts
                of competent jurisdiction located in Ontario, Canada.
            </p>

            <h2 id="dispute-resolution">15. Dispute Resolution</h2>
            <p>
                If you have a dispute with us, we ask that you first contact us at
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a> and allow us 30 days
                to resolve it informally before initiating any formal legal proceeding. Most issues can
                be resolved quickly this way.
            </p>
            <p>
                If informal resolution fails, any dispute shall be submitted to and resolved
                exclusively by the courts of Ontario, Canada. Both parties consent to personal
                jurisdiction in those courts and waive any objection to that venue.
            </p>
            <p>
                Any claim must be brought within one year of the cause of action arising. Claims not
                brought within that period are permanently barred.
            </p>

            <h2 id="corrections">16. Corrections</h2>
            <p>
                There may be information on the Services that contains typographical errors,
                inaccuracies, or omissions. We reserve the right to correct any such errors and to
                update information at any time without prior notice.
            </p>

            <h2 id="disclaimer">17. Disclaimer</h2>
            <p>
                THE SERVICES ARE PROVIDED ON AN AS-IS AND AS-AVAILABLE BASIS WITHOUT ANY WARRANTIES
                OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS
                FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE SERVICES
                WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF HARMFUL COMPONENTS. YOUR USE OF THE
                SERVICES IS ENTIRELY AT YOUR OWN RISK.
            </p>

            <h2 id="liability">18. Limitations of Liability</h2>
            <p>
                TO THE FULLEST EXTENT PERMITTED BY LAW, CRAFTMEET AND ITS OFFICERS, EMPLOYEES, AND
                AGENTS SHALL NOT BE LIABLE FOR ANY INDIRECT, CONSEQUENTIAL, INCIDENTAL, SPECIAL, OR
                PUNITIVE DAMAGES INCLUDING LOST PROFITS, LOST DATA, OR SERVICE INTERRUPTION ARISING
                FROM YOUR USE OF OR INABILITY TO USE THE SERVICES.
            </p>
            <p>
                IN ALL CASES, OUR TOTAL LIABILITY TO YOU FOR ANY CLAIM ARISING OUT OF OR RELATING TO
                THESE TERMS OR THE SERVICES SHALL NOT EXCEED THE GREATER OF (A) THE TOTAL AMOUNT YOU
                PAID US IN THE SIX MONTHS PRECEDING THE CLAIM, OR (B) $100 CAD. THIS LIMITATION
                APPLIES REGARDLESS OF THE FORM OF ACTION OR THE BASIS OF THE CLAIM.
            </p>
            <p>
                SOME JURISDICTIONS DO NOT ALLOW CERTAIN LIABILITY EXCLUSIONS OR LIMITATIONS. IF
                THOSE LAWS APPLY TO YOU, SOME OR ALL OF THE ABOVE MAY NOT APPLY AND YOU MAY HAVE
                ADDITIONAL RIGHTS.
            </p>

            <h2 id="indemnification">19. Indemnification</h2>
            <p>
                You agree to defend, indemnify, and hold harmless Craftmeet and its officers,
                employees, and agents from and against any claims, losses, damages, liabilities, and
                expenses (including reasonable legal fees) arising out of or relating to:
            </p>
            <ul class="text-muted-foreground">
                <li>Your use of the Services.</li>
                <li>Your Contributions.</li>
                <li>Your breach of these Terms.</li>
                <li>
                    Your violation of any third party's rights, including intellectual property
                    rights.
                </li>
                <li>Any harmful act you take against another user of the Services.</li>
            </ul>
            <p>
                We reserve the right to assume exclusive control of any matter subject to
                indemnification by you, at your expense. You agree to cooperate with our defense of
                any such claims.
            </p>

            <h2 id="user-data">20. User Data</h2>
            <p>
                We retain certain data you transmit to the Services for the purpose of managing and
                operating the platform. While we perform routine backups, you are solely responsible
                for maintaining your own copies of any data or exported PDFs you wish to retain.
                Note that AI-generated meeting export PDFs are automatically deleted 24 hours after
                creation. We are not liable for any loss or corruption of your data.
            </p>

            <h2 id="electronic-communications">21. Electronic Communications</h2>
            <p>
                By using the Services or contacting us by email, you consent to receive electronic
                communications from us. You agree that all agreements, notices, and disclosures we
                provide electronically satisfy any legal requirement that such communications be in
                writing.
            </p>

            <h2 id="miscellaneous">22. Miscellaneous</h2>
            <p>
                These Terms, together with our Privacy Notice, constitute the entire agreement
                between you and Craftmeet regarding your use of the Services. If any provision of
                these Terms is found to be unenforceable, the remaining provisions will continue in
                full force and effect. Our failure to enforce any right or provision shall not
                constitute a waiver of that right. We may assign our rights and obligations under
                these Terms without restriction. You may not assign your rights without our prior
                written consent.
            </p>

            <h2 id="contact">23. Contact Us</h2>
            <p>
                If you have questions, concerns, or complaints about these Terms, please contact us
                at <a href="mailto:support@craftmeet.live">support@craftmeet.live</a>. We will
                respond within 30 days.
            </p>
            <address class="not-italic text-muted-foreground">
                <strong class="text-primary">Craftmeet</strong><br />
                Legal inquiries:
                <a href="mailto:support@craftmeet.live">support@craftmeet.live</a><br />
                United States (DigitalOcean NYC)
            </address>
        </article>
    </div>
</main>
