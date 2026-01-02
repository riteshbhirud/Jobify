'use client'

import { Check } from 'lucide-react'

interface ProgressBarProps {
  currentStep: number
  totalSteps: number
}

const STEP_LABELS = ['Personal', 'Education', 'Experience', 'Skills', 'Resume', 'Preferences', 'Finish']

export function ProgressBar({ currentStep, totalSteps }: ProgressBarProps) {
  return (
    <div className="w-full max-w-3xl mx-auto mb-10">
      {/* Desktop: Step indicators with connecting line */}
      <div className="hidden md:block">
        <div className="relative flex items-center justify-between">
          {/* Background line */}
          <div className="absolute top-5 left-0 right-0 h-0.5 bg-muted -z-10" />

          {/* Progress line */}
          <div
            className="absolute top-5 left-0 h-0.5 bg-primary transition-all duration-500 -z-10"
            style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
          />

          {/* Step circles */}
          {STEP_LABELS.slice(0, totalSteps).map((label, index) => {
            const stepNumber = index + 1
            const isCompleted = stepNumber < currentStep
            const isCurrent = stepNumber === currentStep

            return (
              <div key={stepNumber} className="flex flex-col items-center bg-background px-1">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold
                    transition-all duration-300 border-2
                    ${isCompleted
                      ? 'bg-primary border-primary text-white'
                      : isCurrent
                        ? 'bg-primary border-primary text-white shadow-lg shadow-primary/30'
                        : 'bg-background border-muted-foreground/30 text-muted-foreground'
                    }
                  `}
                >
                  {isCompleted ? <Check className="h-5 w-5" /> : stepNumber}
                </div>
                <span
                  className={`
                    mt-2 text-xs font-medium transition-colors
                    ${isCurrent ? 'text-primary' : isCompleted ? 'text-foreground' : 'text-muted-foreground'}
                  `}
                >
                  {label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Mobile: Simple progress bar */}
      <div className="md:hidden">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium">
            Step {currentStep} of {totalSteps}
          </span>
          <span className="text-sm font-medium text-primary">
            {Math.round((currentStep / totalSteps) * 100)}%
          </span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          {STEP_LABELS[currentStep - 1]}
        </p>
      </div>
    </div>
  )
}
