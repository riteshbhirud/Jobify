"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const features = [
  {
    title: "Lightning Fast",
    description:
      "Detects new postings every 2 hours and applies instantly. Be the first applicant, every time.",
  },
  {
    title: "AI Matching",
    description:
      "Smart algorithms that only apply to jobs fitting your skills, experience, and career goals.",
  },
  {
    title: "24/7 Autopilot",
    description:
      "Set preferences once. Wake up to applications submitted and opportunities waiting.",
  },
  {
    title: "Full Control",
    description:
      "Pause anytime. Complete transparency on every application. Your data stays yours.",
  },
  {
    title: "Resume Tailoring",
    description:
      "AI customizes your resume per position, highlighting the most relevant experience.",
  },
  {
    title: "Track Progress",
    description:
      "Real-time dashboard with applications, responses, and interview rates at a glance.",
  },
]

export function Features() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <section id="features" className="py-24 sm:py-32 relative">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-6xl">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mb-16 sm:mb-20"
        >
          <p className="text-sm font-semibold uppercase tracking-widest text-primary mb-4">
            Features
          </p>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground leading-tight max-w-3xl">
            Everything you need to{" "}
            <span className="text-gradient">land your dream job</span>
          </h2>
        </motion.div>

        {/* Features grid */}
        <div ref={ref} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-12 lg:gap-x-16 gap-y-12 sm:gap-y-14">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{
                duration: 0.4,
                delay: index * 0.08,
                ease: [0.25, 0.1, 0.25, 1],
              }}
            >
              {/* Accent line */}
              <div className="h-px w-full bg-border mb-7 relative overflow-hidden">
                <motion.div
                  className="absolute inset-y-0 left-0 bg-primary"
                  initial={{ width: 0 }}
                  animate={isInView ? { width: "2rem" } : { width: 0 }}
                  transition={{ duration: 0.6, delay: 0.3 + index * 0.08 }}
                />
              </div>

              {/* Title */}
              <h3 className="text-2xl font-semibold text-foreground mb-3 tracking-tight">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="text-lg leading-relaxed text-muted-foreground">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
