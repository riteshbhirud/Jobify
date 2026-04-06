"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Check, ArrowRight } from "lucide-react"

const features = [
  "Unlimited job applications",
  "Advanced AI matching",
  "Cover letter generation",
  "Resume optimization",
  "Application analytics",
  "Priority support",
  "Real-time dashboard",
  "All ATS platforms supported",
]

export function Pricing() {
  return (
    <section id="pricing" className="py-24 sm:py-32 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 mesh-gradient opacity-30" />

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
            Pricing
          </motion.span>
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            One plan.
            <span className="text-gradient"> Everything included.</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            No tiers, no upsells. Get full access to every feature at our special launch price.
          </p>
        </motion.div>

        {/* Single pricing card */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-lg mx-auto"
        >
          <div className="relative group">
            {/* Launch offer badge */}
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-20">
              <motion.div
                initial={{ scale: 0 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5, type: "spring" }}
                className="px-5 py-1.5 rounded-full bg-gradient-to-r from-primary to-secondary text-white text-sm font-semibold shadow-glow whitespace-nowrap"
              >
                Launch Offer
              </motion.div>
            </div>

            <div className="p-10 rounded-3xl glass border-2 border-primary/50 shadow-glow hover:shadow-glow-lg transition-all duration-500">
              {/* Plan header */}
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold text-foreground mb-1">
                  Full Access
                </h3>
                <p className="text-muted-foreground text-sm">Everything you need to land your dream job</p>
              </div>

              {/* Price */}
              <div className="text-center mb-8">
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-6xl font-bold text-foreground">$3.99</span>
                  <span className="text-muted-foreground text-lg">/month</span>
                </div>
              </div>

              {/* Divider */}
              <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent mb-8" />

              {/* Features - 2 columns */}
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 mb-10">
                {features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2.5">
                    <Check className="w-4 h-4 text-secondary flex-shrink-0" />
                    <span className="text-sm text-muted-foreground">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Button
                asChild
                className="w-full py-6 text-base bg-gradient-to-r from-primary to-secondary hover:opacity-90 shadow-glow hover:shadow-glow-lg transition-all duration-300 hover:scale-[1.02] group"
              >
                <Link href="/auth/signup" className="flex items-center justify-center gap-2">
                  Get Started — $3.99/mo
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </Button>

            </div>
          </div>
        </motion.div>

        {/* Money back guarantee */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8 }}
          className="text-center text-muted-foreground mt-12"
        >
          14-day money-back guarantee. No questions asked.
        </motion.p>
      </div>
    </section>
  )
}
