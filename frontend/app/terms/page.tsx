// frontend/app/terms/page.tsx

import { Header } from "@/components/layout/Header"
import { Footer } from "@/components/layout/Footer"

export const metadata = {
  title: "Terms and Conditions | ApplyAFK",
  description: "Terms and Conditions for using the ApplyAFK job application automation service.",
}

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <Header />
      <main className="flex-1 py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto prose prose-neutral dark:prose-invert">
          <h1>Terms and Conditions</h1>
          <p className="text-muted-foreground"><strong>Last Updated: February 4, 2026</strong></p>

          <p>
            These Terms and Conditions (&quot;Terms&quot;) govern your use of ApplyAFK (&quot;the Service&quot;),
            a platform provided by ApplyAFK (&quot;ApplyAFK,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;).
            By accessing or using the Service, you agree to be bound by these Terms. If you do not agree
            to these Terms, please do not use the Service.
          </p>

          <hr />

          <h2>1. Acceptance of Terms</h2>
          <p>
            By accessing or using the Service, you agree to be bound by these Terms and all applicable
            laws and regulations. If you do not agree with any of these Terms, you are prohibited from
            using or accessing the Service.
          </p>

          <hr />

          <h2>2. Description of Service</h2>
          <p>
            ApplyAFK is an AI-powered job application automation platform designed to assist users in
            their job search. The Service:
          </p>
          <ul>
            <li>Automatically identifies job opportunities matching your profile and preferences</li>
            <li>Uses artificial intelligence algorithms to match your skills and experience with relevant positions</li>
            <li>Acts as your <strong>authorized agent</strong> to complete and submit job applications on your behalf</li>
            <li>Utilizes browser automation technology to fill out application forms on supported Applicant Tracking System (ATS) platforms</li>
            <li>Generates tailored cover letters and application responses using AI technology</li>
          </ul>
          <p>
            <strong>Important:</strong> ApplyAFK does not scrape, harvest, or collect data from ATS platforms
            for any purpose other than submitting applications on your behalf. We function as an automated
            assistant performing actions you have explicitly authorized—similar to how you might use a
            recruiter or career services professional.
          </p>

          <hr />

          <h2>3. Supported Platforms</h2>
          <p>
            The Service currently supports automated job applications on the following ATS platforms:
          </p>
          <ul>
            <li>Greenhouse</li>
            <li>Lever</li>
            <li>Workable</li>
            <li>Workday</li>
          </ul>
          <p>
            <strong>Platform Limitations:</strong> We are actively working to expand support to additional
            platforms. However, we make no guarantees regarding when specific platforms will be supported,
            the completeness of support for any platform, or continued support for currently supported
            platforms. ATS platforms may change their interfaces or security measures at any time, which
            may temporarily or permanently affect the Service&apos;s functionality. Jobs posted on unsupported
            platforms cannot be automatically applied to through the Service.
          </p>

          <hr />

          <h2>4. Eligibility and Use of the Service</h2>
          <p>
            <strong>Age Requirement:</strong> You must be at least <strong>eighteen (18) years of age</strong> to
            use the Service. By using the Service, you represent and warrant that you are at least 18 years
            old and have the legal capacity to enter into these Terms.
          </p>
          <p>
            <strong>Authorization:</strong> By creating an account, you authorize ApplyAFK to act on your
            behalf for job application purposes, including accessing job portals, filling out application
            forms, uploading your documents, and submitting completed applications to prospective employers.
          </p>

          <hr />

          <h2>5. User Conduct and Responsibilities</h2>
          <p>
            You agree to use the Service only for lawful purposes and in accordance with these Terms.
            You agree not to:
          </p>
          <ul>
            <li>Provide false, misleading, or fraudulent information</li>
            <li>Use the Service to apply for positions for which you are not qualified or authorized</li>
            <li>Misrepresent your qualifications, work authorization status, or any material fact</li>
            <li>Use the Service in any way that violates applicable laws or regulations</li>
            <li>Attempt to reverse engineer, disable, or interfere with the Service&apos;s features</li>
          </ul>
          <p>
            <strong>Your Responsibility:</strong> You are solely responsible for ensuring all information
            in your profile is accurate, complete, and up-to-date. The quality and success of your
            applications depend substantially on the accuracy of the information you provide.
          </p>

          <hr />

          <h2>6. AI Technology and Limitations</h2>

          <h3>6.1 Use of Artificial Intelligence</h3>
          <p>The Service utilizes AI and machine learning technologies, including:</p>
          <ul>
            <li>Language models for generating cover letters and answering application questions</li>
            <li>Embedding models for job matching and compatibility scoring</li>
            <li>Pattern recognition for form field identification and completion</li>
          </ul>

          <h3>6.2 AI Limitations and Potential Inaccuracies</h3>
          <p><strong>YOU EXPRESSLY ACKNOWLEDGE AND AGREE THAT:</strong></p>
          <p>
            <strong>(a) AI-Generated Content May Contain Errors.</strong> Cover letters, application
            responses, and other AI-generated content may occasionally contain inaccuracies, inappropriate
            phrasing, or information that does not perfectly represent your qualifications or intentions.
            While we strive for accuracy, AI systems can produce unexpected or imperfect outputs.
          </p>
          <p>
            <strong>(b) Form Completion May Be Imprecise.</strong> Automated form filling may occasionally
            misinterpret question intent, select suboptimal answers, fail to properly format responses,
            or encounter unfamiliar form layouts that result in errors.
          </p>
          <p>
            <strong>(c) Matching Is Not Perfect.</strong> Job matching algorithms provide recommendations
            based on available data but may not always align perfectly with your preferences or qualifications.
          </p>
          <p>
            <strong>(d) Human Review Recommended.</strong> We strongly recommend periodically reviewing
            your application history and profile settings to ensure accuracy. You retain full responsibility
            for all information submitted on your behalf.
          </p>

          <hr />

          <h2>7. No Guarantees on Outcomes</h2>

          <h3>7.1 Disclaimer of Results</h3>
          <p><strong>APPLYAFK MAKES NO GUARANTEES, REPRESENTATIONS, OR WARRANTIES REGARDING:</strong></p>
          <ul>
            <li>The number of interviews or responses you will receive</li>
            <li>Whether you will receive job offers</li>
            <li>The quality or suitability of job matches</li>
            <li>The success rate of submitted applications</li>
            <li>Any specific employment outcomes</li>
          </ul>

          <h3>7.2 Results Depend on Your Data</h3>
          <p>
            <strong>The effectiveness of the Service is directly correlated with the quality, accuracy,
            and completeness of the information you provide.</strong> Applications are only as good as
            the data used to generate them. Incomplete, outdated, or inaccurate profile information will
            negatively impact application quality and outcomes.
          </p>

          <h3>7.3 External Factors</h3>
          <p>Application success is influenced by numerous factors beyond our control, including:</p>
          <ul>
            <li>Your qualifications relative to other candidates</li>
            <li>Employer hiring decisions, criteria, and timelines</li>
            <li>Economic and job market conditions</li>
            <li>Employer response rates and potential hiring freezes</li>
            <li>Technical issues on employer platforms</li>
            <li>Changes to ATS platform interfaces or requirements</li>
          </ul>

          <h3>7.4 Application Timing</h3>
          <p>
            While we aim to submit applications promptly—typically within the first few hours of
            identifying matching positions—<strong>timing is not guaranteed</strong>. Delays may occur due to:
          </p>
          <ul>
            <li>Technical issues or scheduled maintenance</li>
            <li>High volume of applications being processed</li>
            <li>ATS platform availability or rate limiting</li>
            <li>Network or connectivity issues</li>
            <li>System updates or improvements</li>
            <li>Browser automation session limits</li>
          </ul>

          <hr />

          <h2>8. Limitation of Liability</h2>

          <h3>8.1 Disclaimer of Warranties</h3>
          <p>
            THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF ANY KIND,
            WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY,
            FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
          </p>

          <h3>8.2 Limitation of Liability</h3>
          <p><strong>TO THE FULLEST EXTENT PERMITTED BY APPLICABLE LAW, APPLYAFK SHALL NOT BE LIABLE FOR:</strong></p>
          <ul>
            <li>Any indirect, incidental, special, consequential, or punitive damages</li>
            <li>Any loss of profits, revenue, data, or business opportunities</li>
            <li><strong>Inaccurate, incomplete, or incorrect information in job applications submitted on your behalf</strong></li>
            <li><strong>Errors, omissions, or inaccuracies in AI-generated content including cover letters and application responses</strong></li>
            <li>Missed job opportunities or application deadlines</li>
            <li>Rejection of applications by employers</li>
            <li>Any conduct or content of any third party, including employers and ATS platforms</li>
            <li>Technical failures, service interruptions, or downtime</li>
            <li>Unauthorized access, use, or alteration of your data</li>
            <li>Any employment decisions made by third parties</li>
          </ul>
          <p>
            <strong>IN NO EVENT SHALL OUR TOTAL LIABILITY EXCEED THE AMOUNT YOU HAVE PAID US IN THE
            TWELVE (12) MONTHS PRECEDING THE CLAIM.</strong>
          </p>

          <h3>8.3 Acknowledgment of Risk</h3>
          <p>
            You acknowledge and accept that automated systems may occasionally produce errors, AI
            technology has inherent limitations, job application outcomes are inherently uncertain,
            and third-party platforms are outside our control.
          </p>

          <hr />

          <h2>9. Subscriptions and Payment</h2>

          <h3>9.1 Subscription Plan</h3>
          <p>ApplyAFK offers the following subscription:</p>
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Price</th>
                  <th>Applications</th>
                  <th>Features</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Unlimited</td>
                  <td>$2/month</td>
                  <td>Unlimited</td>
                  <td>AI matching, cover letter generation, application tracking, email notifications, analytics</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3>9.2 Payment Processing</h3>
          <p>
            All payments are processed securely through <strong>Stripe</strong>, a third-party payment
            processor. By subscribing to a paid plan, you agree to:
          </p>
          <ul>
            <li>Stripe&apos;s Terms of Service and Privacy Policy</li>
            <li>Provide accurate and complete payment information</li>
            <li>Authorize recurring charges at the applicable subscription rate</li>
          </ul>

          <h3>9.3 Automatic Renewal</h3>
          <p>
            <strong>Paid subscriptions automatically renew</strong> at the end of each billing period
            (monthly) unless cancelled before the renewal date. Your payment method will be charged
            the then-current subscription rate upon each renewal. You may cancel your subscription at
            any time through your account settings. Cancellation takes effect at the end of the current
            billing period; you will retain access until then.
          </p>

          <h3>9.4 Money-Back Guarantee</h3>
          <p>
            We offer a <strong>14-day money-back guarantee</strong> for first-time subscribers to paid
            plans. If you are not satisfied with the Service within the first 14 days of your initial
            paid subscription, you may request a full refund by contacting support. This guarantee:
          </p>
          <ul>
            <li>Applies only to your first paid subscription</li>
            <li>Must be requested within 14 days of initial payment</li>
            <li>Does not apply to subscription renewals</li>
            <li>Does not apply to users who violate these Terms</li>
          </ul>

          <h3>9.5 Refunds (Outside Money-Back Guarantee)</h3>
          <p>
            Except as provided in the 14-day money-back guarantee, <strong>subscription fees are
            non-refundable</strong>. Partial refunds are not provided for unused portions of billing periods.
          </p>

          <h3>9.6 Price Changes</h3>
          <p>
            We reserve the right to modify subscription prices. Price changes will be communicated in
            advance and will apply to subsequent billing periods, not your current active subscription.
          </p>

          <hr />

          <h2>10. Intellectual Property</h2>
          <p>
            All content included in or made available through the Service—including text, graphics,
            logos, images, software, algorithms, and documentation—is the property of ApplyAFK or its
            licensors and is protected by copyright and other intellectual property laws.
          </p>
          <p>
            You retain ownership of all content you provide (resume, profile information, etc.). By
            using the Service, you grant ApplyAFK a non-exclusive license to use your content solely
            for providing and improving the Service.
          </p>

          <hr />

          <h2>11. Privacy Policy</h2>
          <p>
            Your use of the Service is subject to our Privacy Policy, which is incorporated into these
            Terms by reference. By using the Service, you consent to the collection, use, and disclosure
            of your personal information as described in the Privacy Policy.
          </p>
          <p>
            Your data is processed by AI systems and third-party services (including OpenAI for AI
            processing, Stripe for payments, and cloud infrastructure providers) to deliver the Service
            functionality.
          </p>

          <hr />

          <h2>12. Early Stage Service</h2>
          <p>The Service is under active development. As such:</p>
          <ul>
            <li>Features and functionality may change, expand, or be discontinued</li>
            <li>The Service may experience stability issues or intermittent downtime</li>
            <li>We are continuously working to improve accuracy and expand platform support</li>
          </ul>
          <p>
            We appreciate your patience and feedback as we work to deliver the best possible service.
            By using the Service, you acknowledge that you do so at your own discretion and risk.
          </p>

          <hr />

          <h2>13. Modification of Terms</h2>
          <p>
            ApplyAFK reserves the right to modify these Terms at any time. We will notify you of
            material changes by posting the revised Terms on this page and updating the &quot;Last Updated&quot;
            date. For significant changes, we may also notify you via email. Your continued use of the
            Service after changes are posted constitutes acceptance of the modified Terms.
          </p>

          <hr />

          <h2>14. Termination</h2>
          <p>
            ApplyAFK may terminate or suspend your access to the Service immediately, without prior
            notice or liability, for any reason whatsoever, including without limitation if you breach
            these Terms.
          </p>
          <p>
            You may terminate your account at any time by cancelling your subscription and contacting
            support. Upon termination, your right to use the Service ceases immediately.
          </p>

          <hr />

          <h2>15. Governing Law</h2>
          <p>
            These Terms shall be governed by and construed in accordance with the laws of the
            <strong> Commonwealth of Massachusetts</strong>, United States, without regard to its
            conflict of law provisions. Any disputes arising from these Terms or your use of the
            Service shall be subject to the exclusive jurisdiction of the state and federal courts
            located in Massachusetts.
          </p>

          <hr />

          <h2>16. Compliance with Laws</h2>
          <p>
            You agree to use the Service in compliance with all applicable laws, regulations, and
            guidelines. You are solely responsible for ensuring that your use of the Service adheres
            to legal requirements in your jurisdiction and does not infringe any third party&apos;s rights.
          </p>

          <hr />

          <h2>17. Indemnification</h2>
          <p>
            You agree to indemnify and hold harmless ApplyAFK and its officers, directors, employees,
            and agents from any claims, liabilities, damages, or expenses (including reasonable
            attorneys&apos; fees) arising from your use of the Service, your violation of these Terms,
            any inaccurate information you provide, or your violation of any rights of third parties.
          </p>

          <hr />

          <h2>18. Contact Information</h2>
          <p>If you have any questions about these Terms, please contact us at:</p>
          <p><strong>Email:</strong> support@applyafk.com</p>

          <hr />

          <p className="text-center font-semibold">
            By using the Service, you acknowledge that you have read, understood, and agree to be
            bound by these Terms.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
