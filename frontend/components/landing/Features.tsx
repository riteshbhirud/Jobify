import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const features = [
  {
    icon: "🚀",
    title: "First to Apply",
    description: "Our system detects new job postings every 2 hours and applies immediately. Beat the competition before they even see the listing."
  },
  {
    icon: "🎯",
    title: "Smart Matching",
    description: "AI-powered matching ensures you only apply to jobs that fit your skills, experience, and preferences. No spam applications."
  },
  {
    icon: "😴",
    title: "You Sleep, We Apply",
    description: "Set your preferences once. Wake up to applications submitted, interviews scheduled, and opportunities waiting."
  },
  {
    icon: "🔒",
    title: "Your Data, Your Control",
    description: "Pause anytime. Full transparency on every application. Your information is never shared."
  }
]

export function Features() {
  return (
    <section id="features" className="py-16 sm:py-24 bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4">
            Why Choose Jobify?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Your personal job application assistant working 24/7
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <Card key={feature.title} className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <div className="text-4xl mb-2">{feature.icon}</div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
