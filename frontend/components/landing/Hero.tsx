import Link from "next/link"
import { Button } from "@/components/ui/button"

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 to-background pt-20 pb-16 sm:pt-32 sm:pb-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl mb-6">
            Never Miss Your{" "}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Dream Job
            </span>{" "}
            Again
          </h1>
          <p className="text-lg text-muted-foreground sm:text-xl max-w-2xl mx-auto mb-8">
            We automatically apply to matching jobs within minutes of posting.
            Be the first applicant, every time.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button asChild size="lg" className="text-base px-8">
              <Link href="/auth/signup">
                Get Started Free
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="text-base px-8">
              <a href="#how-it-works">
                See How It Works
              </a>
            </Button>
          </div>

          <div className="mt-12 text-sm text-muted-foreground">
            <p>Trusted by 500+ job seekers • 10,000+ applications submitted</p>
          </div>
        </div>
      </div>
    </section>
  )
}
