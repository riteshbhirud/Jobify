// frontend/app/privacy/page.tsx

import { Header } from "@/components/layout/Header"
import { Footer } from "@/components/layout/Footer"

export const metadata = {
  title: "Privacy Policy | ApplyAFK",
  description: "Privacy Policy for the ApplyAFK job application automation service.",
}

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <Header />
      <main className="flex-1 py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto prose prose-neutral dark:prose-invert">
          <h1>Privacy Policy</h1>
          <p className="text-muted-foreground"><strong>Last Updated: February 4, 2026</strong></p>

          <p>
            This Privacy Policy describes how ApplyAFK (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) collects, uses,
            and shares your personal information when you use our service (&quot;the Service&quot;). By using the
            Service, you agree to the collection and use of information in accordance with this Privacy Policy.
          </p>

          <hr />

          <h2>1. Information We Collect</h2>

          <h3>1.1 Information You Provide</h3>
          <p>We collect information that you provide directly to us, including:</p>
          <ul>
            <li><strong>Account Information:</strong> Email address, name, and password when you create an account</li>
            <li><strong>Profile Information:</strong> Resume, work experience, education, skills, and job preferences</li>
            <li><strong>Application Data:</strong> Cover letters, application responses, and other materials generated for job applications</li>
            <li><strong>Payment Information:</strong> Billing information processed through Stripe (we do not store your credit card details)</li>
            <li><strong>Communications:</strong> Messages you send to us, feedback, and support requests</li>
          </ul>

          <h3>1.2 Information Automatically Collected</h3>
          <p>When you use the Service, we automatically collect certain information, including:</p>
          <ul>
            <li><strong>Usage Data:</strong> Information about how you interact with the Service, including pages visited, features used, and actions taken</li>
            <li><strong>Device Information:</strong> Browser type, operating system, IP address, and device identifiers</li>
            <li><strong>Application Activity:</strong> Jobs applied to, application status, and employer responses</li>
            <li><strong>Cookies and Similar Technologies:</strong> We use cookies and similar tracking technologies to maintain sessions and enhance user experience</li>
          </ul>

          <hr />

          <h2>2. How We Use Your Information</h2>

          <h3>2.1 To Provide the Service</h3>
          <ul>
            <li>Process and submit job applications on your behalf</li>
            <li>Generate cover letters and application responses using AI technology</li>
            <li>Match your profile with relevant job opportunities</li>
            <li>Track application status and notify you of updates</li>
            <li>Manage your account and subscription</li>
          </ul>

          <h3>2.2 To Improve the Service</h3>
          <ul>
            <li>Analyze usage patterns to improve features and functionality</li>
            <li>Train and improve our AI models and algorithms</li>
            <li>Debug technical issues and optimize performance</li>
            <li>Conduct research and development</li>
          </ul>

          <h3>2.3 To Communicate With You</h3>
          <ul>
            <li>Send application confirmations and status updates</li>
            <li>Respond to your inquiries and support requests</li>
            <li>Send service-related announcements and updates</li>
            <li>Send marketing communications (with your consent)</li>
          </ul>

          <h3>2.4 For Legal and Security Purposes</h3>
          <ul>
            <li>Comply with legal obligations and respond to legal requests</li>
            <li>Protect our rights, property, and safety</li>
            <li>Detect, prevent, and address fraud and security issues</li>
            <li>Enforce our Terms of Service</li>
          </ul>

          <hr />

          <h2>3. How We Share Your Information</h2>

          <h3>3.1 With Your Consent</h3>
          <p>
            We submit job applications containing your information (resume, cover letters, responses) to
            prospective employers on your behalf. This is the core function of the Service and is done
            with your explicit authorization.
          </p>

          <h3>3.2 With Service Providers</h3>
          <p>We share information with third-party service providers who perform services on our behalf:</p>
          <ul>
            <li><strong>AI Processing:</strong> OpenAI and other AI service providers to generate content and match jobs</li>
            <li><strong>Payment Processing:</strong> Stripe for secure payment processing</li>
            <li><strong>Cloud Infrastructure:</strong> Hosting and database providers</li>
            <li><strong>Email Services:</strong> Email delivery providers for notifications</li>
            <li><strong>Analytics:</strong> Analytics providers to understand usage patterns</li>
          </ul>
          <p>
            These service providers are contractually obligated to protect your information and use it
            only for the purposes we specify.
          </p>

          <h3>3.3 For Legal Reasons</h3>
          <p>We may disclose your information if required to do so by law or in response to:</p>
          <ul>
            <li>Legal process, such as a court order or subpoena</li>
            <li>Government or regulatory requests</li>
            <li>Enforcement of our Terms of Service</li>
            <li>Protection of our rights, property, or safety, or that of others</li>
          </ul>

          <h3>3.4 Business Transfers</h3>
          <p>
            If ApplyAFK is involved in a merger, acquisition, or sale of assets, your information may be
            transferred as part of that transaction. We will notify you before your information becomes
            subject to a different privacy policy.
          </p>

          <hr />

          <h2>4. Data Retention</h2>
          <p>
            We retain your personal information for as long as necessary to provide the Service and fulfill
            the purposes described in this Privacy Policy. Specific retention periods include:
          </p>
          <ul>
            <li><strong>Account Data:</strong> Retained while your account is active and for a reasonable period after account closure</li>
            <li><strong>Application History:</strong> Retained for the duration of your subscription and for a limited time thereafter</li>
            <li><strong>Payment Records:</strong> Retained as required for tax and accounting purposes (typically 7 years)</li>
            <li><strong>Usage Logs:</strong> Typically retained for 90 days unless needed for security or legal purposes</li>
          </ul>
          <p>
            You may request deletion of your data at any time by contacting us. Please note that we may
            retain certain information as required by law or for legitimate business purposes.
          </p>

          <hr />

          <h2>5. Data Security</h2>
          <p>
            We implement appropriate technical and organizational measures to protect your personal
            information against unauthorized access, alteration, disclosure, or destruction. These measures include:
          </p>
          <ul>
            <li>Encryption of data in transit (HTTPS/TLS) and at rest</li>
            <li>Secure authentication and access controls</li>
            <li>Regular security assessments and monitoring</li>
            <li>Restricted access to personal information on a need-to-know basis</li>
            <li>Secure password storage using industry-standard hashing</li>
          </ul>
          <p>
            <strong>However, no method of transmission over the Internet or electronic storage is 100%
            secure.</strong> While we strive to use commercially acceptable means to protect your information,
            we cannot guarantee its absolute security.
          </p>

          <hr />

          <h2>6. Your Rights and Choices</h2>

          <h3>6.1 Access and Correction</h3>
          <p>
            You can access and update your account information at any time through your account settings.
            If you need assistance accessing or correcting your information, please contact us.
          </p>

          <h3>6.2 Data Portability</h3>
          <p>
            You have the right to request a copy of your personal information in a structured,
            machine-readable format. Contact us to request a data export.
          </p>

          <h3>6.3 Deletion</h3>
          <p>
            You can request deletion of your account and personal information at any time. Please note
            that we may retain certain information as required by law or for legitimate business purposes.
          </p>

          <h3>6.4 Opt-Out of Marketing</h3>
          <p>
            You can opt out of marketing emails by clicking the &quot;unsubscribe&quot; link in any marketing
            email or by updating your preferences in account settings. You cannot opt out of service-related
            communications (e.g., account notifications, application confirmations).
          </p>

          <h3>6.5 Rights Under GDPR (for EEA Users)</h3>
          <p>If you are located in the European Economic Area, you have additional rights under GDPR:</p>
          <ul>
            <li>Right to access your personal data</li>
            <li>Right to rectification of inaccurate data</li>
            <li>Right to erasure (&quot;right to be forgotten&quot;)</li>
            <li>Right to restrict processing</li>
            <li>Right to data portability</li>
            <li>Right to object to processing</li>
            <li>Right to withdraw consent at any time</li>
          </ul>

          <h3>6.6 Rights Under CCPA (for California Users)</h3>
          <p>If you are a California resident, you have rights under the California Consumer Privacy Act (CCPA):</p>
          <ul>
            <li>Right to know what personal information is collected, used, shared, or sold</li>
            <li>Right to delete personal information</li>
            <li>Right to opt-out of the sale of personal information (we do not sell your personal information)</li>
            <li>Right to non-discrimination for exercising your privacy rights</li>
          </ul>

          <hr />

          <h2>7. AI and Data Processing</h2>
          <p>
            We use artificial intelligence and machine learning technologies to provide the Service,
            including generating cover letters, matching jobs, and answering application questions.
          </p>
          <ul>
            <li>Your data may be processed by third-party AI service providers (including OpenAI)</li>
            <li>We take measures to minimize data sharing and protect your privacy</li>
            <li>AI-generated content is reviewed and filtered for accuracy and appropriateness</li>
            <li>We do not use your data to train publicly available AI models without your consent</li>
          </ul>

          <hr />

          <h2>8. Cookies and Tracking Technologies</h2>
          <p>We use cookies and similar tracking technologies to:</p>
          <ul>
            <li>Maintain your session and authentication</li>
            <li>Remember your preferences and settings</li>
            <li>Analyze usage and improve the Service</li>
          </ul>
          <p>
            You can control cookies through your browser settings. However, disabling cookies may affect
            the functionality of the Service.
          </p>
          <h3>Types of Cookies We Use:</h3>
          <ul>
            <li><strong>Essential Cookies:</strong> Required for the Service to function (e.g., authentication)</li>
            <li><strong>Analytics Cookies:</strong> Help us understand how users interact with the Service</li>
            <li><strong>Preference Cookies:</strong> Remember your settings and preferences</li>
          </ul>

          <hr />

          <h2>9. Children&apos;s Privacy</h2>
          <p>
            The Service is not intended for individuals under the age of 18. We do not knowingly collect
            personal information from children under 18. If you become aware that a child has provided us
            with personal information, please contact us, and we will take steps to delete such information.
          </p>

          <hr />

          <h2>10. International Data Transfers</h2>
          <p>
            Your information may be transferred to and processed in countries other than your country of
            residence, including the United States. These countries may have different data protection
            laws than your country.
          </p>
          <p>
            We take appropriate safeguards to ensure that your personal information remains protected in
            accordance with this Privacy Policy, including using Standard Contractual Clauses and ensuring
            service providers comply with applicable data protection frameworks.
          </p>

          <hr />

          <h2>11. Third-Party Links</h2>
          <p>
            The Service may contain links to third-party websites, services, or job application portals.
            We are not responsible for the privacy practices of these third parties. We encourage you to
            review the privacy policies of any third-party sites you visit.
          </p>

          <hr />

          <h2>12. Changes to This Privacy Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. We will notify you of material changes by
            posting the updated Privacy Policy on this page and updating the &quot;Last Updated&quot; date. For
            significant changes, we may also notify you via email. Your continued use of the Service after
            changes are posted constitutes acceptance of the updated Privacy Policy.
          </p>

          <hr />

          <h2>13. Contact Us</h2>
          <p>If you have questions or concerns about this Privacy Policy or our data practices, please contact us at:</p>
          <p><strong>Email:</strong> support@applyafk.com</p>

          <hr />

          <p className="text-center font-semibold">
            By using the Service, you acknowledge that you have read and understood this Privacy Policy.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
