import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const faqs = [
  {
    question: "Is this legal?",
    answer: "Absolutely! We act as your authorized agent, similar to using a recruiter. You maintain full control and can pause or stop at any time."
  },
  {
    question: "Which job boards do you support?",
    answer: "We support Greenhouse, Lever, Workday, and 50+ other ATS platforms. We're constantly adding new integrations."
  },
  {
    question: "Can I pause anytime?",
    answer: "Yes, you can pause and resume your automation with a single click from your dashboard. No questions asked."
  },
  {
    question: "What if I get too many interviews?",
    answer: "Good problem to have! You can pause applications immediately or adjust your daily application limit at any time."
  },
  {
    question: "How do you match me with jobs?",
    answer: "Our AI analyzes your resume, skills, and preferences to match you with relevant positions. You can set minimum match thresholds and exclusion criteria."
  },
  {
    question: "Is my data secure?",
    answer: "Yes, we use enterprise-grade encryption and never share your data with third parties. Your information is only used for job applications you authorize."
  }
]

export function FAQ() {
  return (
    <section id="faq" className="py-16 sm:py-24 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Everything you need to know about Jobify
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {faqs.map((faq) => (
            <Card key={faq.question}>
              <CardHeader>
                <CardTitle className="text-lg">{faq.question}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base">{faq.answer}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
