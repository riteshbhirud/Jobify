"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"
import { X, Check } from "lucide-react"

const comparison = [
  {
    pain: "Keep a browser session running 24/7",
    gain: "Runs in the cloud — nothing to keep open",
  },
  {
    pain: "Stops when your laptop sleeps",
    gain: "Works while you sleep, travel, or interview",
  },
  {
    pain: "One-size-fits-all applications",
    gain: "AI-tailored resume for every single role",
  },
  {
    pain: "Miss roles posted while you're offline",
    gain: "Applies within minutes of a job going live",
  },
]

const differentiators = [
  {
    title: "No device. No tab. No session.",
    description:
      "AI browsers need your machine running and a session alive. Close the lid and everything stops. ApplyAFK runs on our infrastructure — there is nothing for you to keep open.",
  },
  {
    title: "First applicant advantage",
    description:
      "We scan job boards every 2 hours and apply within minutes of a new posting. Hiring managers often review the first batch and ignore the rest. Timing matters more than you think.",
  },
  {
    title: "Precision matching, not spray-and-pray",
    description:
      "AI browsers apply to whatever you point them at. We use embeddings to match your actual qualifications — skills, experience level, location — so every application is relevant.",
  },
]

export function WhyApplyAFK() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <section className="py-24 sm:py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-transparent to-transparent pointer-events-none" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-16 sm:mb-20"
        >
          <p className="text-sm font-semibold uppercase tracking-widest text-primary mb-4">
            Why not just use an AI browser?
          </p>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground leading-[1.1]">
            They stop when you stop.
            <br />
            <span className="text-gradient">We don&apos;t.</span>
          </h2>
        </motion.div>

        {/* Comparison — row-based */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-24 sm:mb-28"
        >
          {/* Column headers */}
          <div className="grid grid-cols-2 gap-4 sm:gap-6 mb-2 px-1">
            <p className="text-xs sm:text-sm font-semibold text-muted-foreground/50 uppercase tracking-widest">
              AI Browsers
            </p>
            <p className="text-xs sm:text-sm font-semibold text-primary uppercase tracking-widest">
              ApplyAFK
            </p>
          </div>

          {/* Rows */}
          <div className="space-y-0">
            {comparison.map((row, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.35, delay: 0.15 + index * 0.07 }}
                className="grid grid-cols-2 gap-4 sm:gap-6 border-t border-border py-5 sm:py-6"
              >
                {/* Pain */}
                <div className="flex items-start gap-3">
                  <X className="w-5 h-5 text-muted-foreground/30 mt-0.5 flex-shrink-0" />
                  <span className="text-lg sm:text-xl text-muted-foreground/60 line-through decoration-muted-foreground/20">
                    {row.pain}
                  </span>
                </div>
                {/* Gain */}
                <div className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-lg sm:text-xl text-foreground font-medium">
                    {row.gain}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
          <div className="border-t border-border" />
        </motion.div>

        {/* Differentiators — no icons, just typography */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 lg:gap-14">
          {differentiators.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: 0.3 + index * 0.1 }}
            >
              {/* Accent line */}
              <div className="h-px w-full bg-border mb-7 relative overflow-hidden">
                <motion.div
                  className="absolute inset-y-0 left-0 bg-primary"
                  initial={{ width: 0 }}
                  animate={isInView ? { width: "2rem" } : {}}
                  transition={{ duration: 0.6, delay: 0.4 + index * 0.1 }}
                />
              </div>

              <h3 className="text-2xl font-semibold text-foreground mb-3 tracking-tight">
                {item.title}
              </h3>
              <p className="text-lg leading-relaxed text-muted-foreground">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
