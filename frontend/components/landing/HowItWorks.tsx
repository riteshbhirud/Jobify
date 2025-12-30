"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { useRef } from "react"
import { Upload, Settings, Rocket, CheckCircle2 } from "lucide-react"

const steps = [
  {
    step: "01",
    icon: Upload,
    title: "Upload Your Resume",
    time: "2 minutes",
    description: "Simply upload your resume. Our AI extracts your skills, experience, and education automatically to build your profile.",
    color: "primary",
  },
  {
    step: "02",
    icon: Settings,
    title: "Set Your Preferences",
    time: "3 minutes",
    description: "Tell us your dream role, preferred locations, salary expectations, and any deal-breakers. Be as specific as you want.",
    color: "secondary",
  },
  {
    step: "03",
    icon: Rocket,
    title: "Activate & Relax",
    time: "10 seconds",
    description: "Flip the switch and let our AI take over. We'll apply to matching jobs 24/7 while you focus on what matters most.",
    color: "accent",
  },
]

export function HowItWorks() {
  const containerRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  })

  const lineHeight = useTransform(scrollYProgress, [0.1, 0.9], ["0%", "100%"])

  return (
    <section
      id="how-it-works"
      ref={containerRef}
      className="py-24 sm:py-32 relative overflow-hidden bg-gradient-to-b from-background via-muted/20 to-background"
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-block px-4 py-1.5 rounded-full glass text-sm font-medium text-primary mb-4"
          >
            How It Works
          </motion.span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            Get started in
            <span className="text-gradient"> under 5 minutes</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Three simple steps to automate your entire job search
          </p>
        </motion.div>

        {/* Steps */}
        <div className="max-w-4xl mx-auto relative">
          {/* Animated progress line */}
          <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-0.5 bg-border md:-translate-x-1/2 hidden sm:block">
            <motion.div
              className="w-full bg-gradient-to-b from-primary via-secondary to-primary rounded-full"
              style={{ height: lineHeight }}
            />
          </div>

          {steps.map((step, index) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, x: index % 2 === 0 ? -50 : 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
              className={`relative flex items-center mb-16 last:mb-0 ${
                index % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              }`}
            >
              {/* Step indicator (mobile) */}
              <div className="absolute left-0 sm:hidden w-16 h-16 rounded-full glass flex items-center justify-center border-2 border-primary/30 z-10">
                <span className="text-2xl font-bold text-gradient">{step.step}</span>
              </div>

              {/* Content card */}
              <div
                className={`flex-1 ml-20 sm:ml-0 ${
                  index % 2 === 0 ? "md:mr-auto md:pr-16" : "md:ml-auto md:pl-16"
                } md:w-[calc(50%-2rem)]`}
              >
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  className="p-8 rounded-3xl glass border border-white/20 hover:border-primary/30 transition-all duration-300 hover:shadow-glow"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div
                      className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${
                        step.color === "primary"
                          ? "from-primary to-primary/60"
                          : step.color === "secondary"
                          ? "from-secondary to-secondary/60"
                          : "from-purple-500 to-pink-500"
                      } flex items-center justify-center shadow-lg`}
                    >
                      <step.icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-foreground">
                        {step.title}
                      </h3>
                      <p className="text-sm text-primary font-medium">{step.time}</p>
                    </div>
                  </div>
                  <p className="text-muted-foreground leading-relaxed">
                    {step.description}
                  </p>
                </motion.div>
              </div>

              {/* Step indicator (desktop) */}
              <div className="hidden md:flex absolute left-1/2 -translate-x-1/2 w-16 h-16 rounded-full glass items-center justify-center border-2 border-primary/30 z-10 bg-background">
                <span className="text-2xl font-bold text-gradient">{step.step}</span>
              </div>
            </motion.div>
          ))}

          {/* Completion indicator */}
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="flex justify-center mt-8"
          >
            <div className="flex items-center gap-3 px-6 py-3 rounded-full glass border-2 border-secondary/30">
              <CheckCircle2 className="w-6 h-6 text-secondary" />
              <span className="font-semibold text-foreground">
                You&apos;re all set! Applications start automatically.
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
