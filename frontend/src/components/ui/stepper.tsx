import { Check } from "lucide-react"
import { cn } from "../../lib/utils"

interface StepperProps {
  steps: string[]
  currentStep: number
}

export function Stepper({ steps, currentStep }: StepperProps) {
  return (
    <>
      {/* Compact stepper for mobile */}
      <div className="lg:hidden text-sm text-muted-foreground">
        <span className="font-medium text-foreground">
          Шаг {currentStep + 1} из {steps.length}
        </span>
        {" — "}
        <span>{steps[currentStep]}</span>
      </div>

      {/* Full stepper for desktop */}
      <div className="hidden lg:flex items-center gap-2">
        {steps.map((label, index) => (
          <div key={label} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium border-2",
                  index < currentStep
                    ? "bg-primary border-primary text-primary-foreground"
                    : index === currentStep
                      ? "border-primary text-primary bg-background"
                      : "border-muted-foreground/30 text-muted-foreground bg-background"
                )}
              >
                {index < currentStep ? <Check className="w-4 h-4" /> : index + 1}
              </div>
              <span
                className={cn(
                  "text-sm whitespace-nowrap",
                  index <= currentStep ? "font-medium text-foreground" : "text-muted-foreground"
                )}
              >
                {label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "h-px w-8 mx-1",
                  index < currentStep ? "bg-primary" : "bg-muted-foreground/30"
                )}
              />
            )}
          </div>
        ))}
      </div>
    </>
  )
}
