const steps = [
  {
    step: "1",
    title: "Upload Your Resume",
    time: "2 minutes",
    description: "We extract your skills, experience, and education automatically."
  },
  {
    step: "2",
    title: "Set Your Preferences",
    time: "3 minutes",
    description: "Tell us your target role, locations, salary expectations, and deal-breakers."
  },
  {
    step: "3",
    title: "Activate & Relax",
    time: "10 seconds",
    description: "Flip the switch. We handle the rest. Track everything in your dashboard."
  }
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-16 sm:py-24 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4">
            How It Works
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Get started in less than 10 minutes
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {steps.map((item, index) => (
            <div key={item.step} className="relative">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold mb-4">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-sm text-primary font-medium mb-2">{item.time}</p>
                <p className="text-muted-foreground">
                  {item.description}
                </p>
              </div>
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-8 left-1/2 w-full h-0.5 bg-border" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
