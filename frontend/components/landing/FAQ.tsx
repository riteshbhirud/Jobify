"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, HelpCircle } from "lucide-react"

const faqs = [
  {
    question: "Is this legal?",
    answer:
      "Absolutely! We act as your authorized agent, similar to using a recruiter. You maintain full control and can pause or stop at any time. All applications are submitted on your behalf with your explicit consent.",
  },
  {
    question: "Which job boards do you support?",
    answer:
      "We support Greenhouse, Lever, Workday, Ashby, and 50+ other ATS platforms. We're constantly adding new integrations based on user requests. If you need a specific platform, let us know!",
  },
  {
    question: "Can I pause anytime?",
    answer:
      "Yes, you can pause and resume your automation with a single click from your dashboard. No questions asked, no waiting period. Your preferences are saved for when you're ready to resume.",
  },
  {
    question: "What if I get too many interviews?",
    answer:
      "Good problem to have! You can pause applications immediately, adjust your daily application limit, or refine your matching criteria at any time. We recommend starting with fewer applications and scaling up.",
  },
  {
    question: "How do you match me with jobs?",
    answer:
      "Our AI analyzes your resume, skills, and preferences to match you with relevant positions. You can set minimum match thresholds, exclusion criteria, and even specific companies to target or avoid.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes, we use enterprise-grade encryption (AES-256) and never share your data with third parties. Your information is only used for job applications you authorize. We're SOC 2 compliant.",
  },
]

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  return (
    <section
      id="faq"
      className="py-24 sm:py-32 relative overflow-hidden bg-gradient-to-b from-muted/30 via-background to-muted/30"
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-block px-4 py-1.5 rounded-full glass text-sm font-medium text-primary mb-4"
          >
            FAQ
          </motion.span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            Frequently asked
            <span className="text-gradient"> questions</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Everything you need to know about Jobify
          </p>
        </motion.div>

        {/* FAQ items */}
        <div className="max-w-3xl mx-auto">
          {faqs.map((faq, index) => (
            <motion.div
              key={faq.question}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
              className="mb-4"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className={`w-full p-6 rounded-2xl glass border text-left transition-all duration-300 group ${
                  openIndex === index
                    ? "border-primary/30 shadow-glow"
                    : "border-white/20 hover:border-primary/20"
                }`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-300 ${
                        openIndex === index
                          ? "bg-primary text-white"
                          : "bg-primary/10 text-primary"
                      }`}
                    >
                      <HelpCircle className="w-5 h-5" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
                      {faq.question}
                    </h3>
                  </div>
                  <motion.div
                    animate={{ rotate: openIndex === index ? 180 : 0 }}
                    transition={{ duration: 0.3 }}
                    className="flex-shrink-0"
                  >
                    <ChevronDown
                      className={`w-5 h-5 transition-colors duration-300 ${
                        openIndex === index ? "text-primary" : "text-muted-foreground"
                      }`}
                    />
                  </motion.div>
                </div>

                <AnimatePresence>
                  {openIndex === index && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="pt-4 pl-14 text-muted-foreground leading-relaxed">
                        {faq.answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </button>
            </motion.div>
          ))}
        </div>

        {/* Contact CTA */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center mt-16"
        >
          <p className="text-muted-foreground mb-4">
            Still have questions?
          </p>
          <a
            href="mailto:support@jobify.com"
            className="inline-flex items-center gap-2 text-primary hover:text-primary/80 font-medium transition-colors"
          >
            Contact our support team
            <span className="text-lg">→</span>
          </a>
        </motion.div>
      </div>
    </section>
  )
}
