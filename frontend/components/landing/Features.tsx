"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"
import { Zap, Target, Moon, Shield, Brain, TrendingUp } from "lucide-react"

const features = [
  {
    icon: Zap,
    title: "Lightning Fast Applications",
    description: "Our system detects new job postings every 2 hours and applies immediately. Be the first applicant, every time.",
    gradient: "from-yellow-500 to-orange-500",
  },
  {
    icon: Target,
    title: "AI-Powered Matching",
    description: "Smart algorithms ensure you only apply to jobs that truly fit your skills, experience, and career goals.",
    gradient: "from-primary to-blue-500",
  },
  {
    icon: Moon,
    title: "24/7 Autopilot",
    description: "Set your preferences once. Wake up to applications submitted, interviews scheduled, and opportunities waiting.",
    gradient: "from-purple-500 to-pink-500",
  },
  {
    icon: Shield,
    title: "Full Control & Privacy",
    description: "Pause anytime with one click. Complete transparency on every application. Your data is never shared.",
    gradient: "from-green-500 to-emerald-500",
  },
  {
    icon: Brain,
    title: "Smart Resume Tailoring",
    description: "AI customizes your resume for each position, highlighting the most relevant experience and skills.",
    gradient: "from-cyan-500 to-blue-500",
  },
  {
    icon: TrendingUp,
    title: "Track Your Progress",
    description: "Real-time dashboard shows applications, responses, and interview rates. Optimize your job search.",
    gradient: "from-rose-500 to-red-500",
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1] as const,
    },
  },
}

export function Features() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section id="features" className="py-24 sm:py-32 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 mesh-gradient opacity-50" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16 sm:mb-20"
        >
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-block px-4 py-1.5 rounded-full glass text-sm font-medium text-primary mb-4"
          >
            Features
          </motion.span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            Everything you need to
            <span className="text-gradient block sm:inline"> land your dream job</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Your personal job application assistant working around the clock, so you can focus on preparing for interviews
          </p>
        </motion.div>

        {/* Features grid */}
        <motion.div
          ref={ref}
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8"
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              variants={cardVariants}
              className="group relative"
            >
              <div className="h-full p-8 rounded-3xl glass hover-lift transition-all duration-500 border border-white/20 hover:border-primary/30">
                {/* Icon container */}
                <div
                  className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform duration-300`}
                >
                  <feature.icon className="w-7 h-7 text-white" />
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-foreground mb-3 group-hover:text-primary transition-colors">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>

                {/* Hover gradient overlay */}
                <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-primary/5 to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
