"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Check, Sparkles, Zap, Crown } from "lucide-react"

const plans = [
  {
    name: "Free",
    icon: Sparkles,
    price: "$0",
    period: "/month",
    description: "Perfect for getting started",
    features: [
      "3 applications per day",
      "Basic job matching",
      "Email notifications",
      "Application tracking",
      "Standard support",
    ],
    cta: "Start Free",
    popular: false,
    gradient: "from-gray-500/10 to-gray-600/10",
    iconGradient: "from-gray-500 to-gray-600",
  },
  {
    name: "Starter",
    icon: Zap,
    price: "$29",
    period: "/month",
    description: "For active job seekers",
    features: [
      "10 applications per day",
      "Advanced AI matching",
      "Priority notifications",
      "Resume optimization tips",
      "Priority support",
      "Application analytics",
    ],
    cta: "Get Started",
    popular: true,
    gradient: "from-primary/20 to-secondary/20",
    iconGradient: "from-primary to-secondary",
  },
  {
    name: "Pro",
    icon: Crown,
    price: "$79",
    period: "/month",
    description: "For maximum reach",
    features: [
      "25 applications per day",
      "AI-tailored resumes",
      "Cover letter generation",
      "Interview prep resources",
      "Dedicated support",
      "Advanced analytics",
      "Early access to features",
    ],
    cta: "Go Pro",
    popular: false,
    gradient: "from-purple-500/10 to-pink-500/10",
    iconGradient: "from-purple-500 to-pink-500",
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
}

const cardVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1] as const,
    },
  },
}

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
            Simple, transparent
            <span className="text-gradient"> pricing</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Choose the plan that fits your job search. Upgrade or downgrade anytime.
          </p>
        </motion.div>

        {/* Pricing cards */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto"
        >
          {plans.map((plan) => (
            <motion.div
              key={plan.name}
              variants={cardVariants}
              whileHover={{ y: -8 }}
              className={`relative group ${plan.popular ? "md:-mt-4 md:mb-4" : ""}`}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-20">
                  <motion.div
                    initial={{ scale: 0 }}
                    whileInView={{ scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5, type: "spring" }}
                    className="px-4 py-1.5 rounded-full bg-gradient-to-r from-primary to-secondary text-white text-sm font-semibold shadow-glow"
                  >
                    Most Popular
                  </motion.div>
                </div>
              )}

              <div
                className={`h-full p-8 rounded-3xl glass border-2 transition-all duration-500 ${
                  plan.popular
                    ? "border-primary/50 shadow-glow"
                    : "border-white/20 hover:border-primary/30"
                }`}
              >
                {/* Plan header */}
                <div className="text-center mb-8">
                  <div
                    className={`w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br ${plan.iconGradient} flex items-center justify-center mb-4 shadow-lg`}
                  >
                    <plan.icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-foreground mb-2">
                    {plan.name}
                  </h3>
                  <p className="text-muted-foreground text-sm">{plan.description}</p>
                </div>

                {/* Price */}
                <div className="text-center mb-8">
                  <span className="text-5xl font-bold text-foreground">{plan.price}</span>
                  <span className="text-muted-foreground">{plan.period}</span>
                </div>

                {/* Features */}
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <div className="mt-0.5">
                        <Check className="w-5 h-5 text-secondary" />
                      </div>
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <Button
                  asChild
                  className={`w-full py-6 text-base transition-all duration-300 ${
                    plan.popular
                      ? "bg-gradient-to-r from-primary to-secondary hover:opacity-90 shadow-glow hover:shadow-glow-lg"
                      : "glass hover:bg-primary/10"
                  }`}
                  variant={plan.popular ? "default" : "outline"}
                >
                  <Link href="/auth/signup">{plan.cta}</Link>
                </Button>
              </div>
            </motion.div>
          ))}
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
