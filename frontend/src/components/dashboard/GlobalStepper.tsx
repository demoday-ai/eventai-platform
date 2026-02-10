import { useState, useEffect } from "react"
import { useLocation } from "react-router-dom"
import { Check, Circle, Loader2 } from "lucide-react"
import { usePipelineStatus } from "../../hooks/usePipelineStatus"
import type { PipelinePhase } from "../../lib/api-client"

function PhaseIcon({ status }: { status: PipelinePhase["status"] }) {
  if (status === "completed") {
    return <Check className="w-4 h-4 text-white" />
  }
  if (status === "in_progress") {
    return <Loader2 className="w-4 h-4 text-white animate-spin" />
  }
  return <Circle className="w-4 h-4 text-muted-foreground" />
}

function StepIcon({ status }: { status: string }) {
  if (status === "completed") {
    return <Check className="w-3 h-3 text-green-600 shrink-0" />
  }
  return <Circle className="w-3 h-3 text-muted-foreground shrink-0" />
}

function getPhaseStyles(status: PipelinePhase["status"]) {
  if (status === "completed") {
    return "bg-green-600 text-white"
  }
  if (status === "in_progress") {
    return "bg-blue-600 text-white"
  }
  return "bg-muted text-muted-foreground"
}

function getConnectorStyles(status: PipelinePhase["status"]) {
  if (status === "completed") {
    return "bg-green-600"
  }
  return "bg-muted"
}

export function GlobalStepper() {
  const { data } = usePipelineStatus()
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null)
  const location = useLocation()

  // Close expanded phase on route change
  useEffect(() => {
    setExpandedPhase(null)
  }, [location.pathname])

  if (!data) return null

  const handlePhaseClick = (phase: PipelinePhase) => {
    setExpandedPhase(expandedPhase === phase.name ? null : phase.name)
  }

  const expandedData = expandedPhase
    ? data.phases.find((p) => p.name === expandedPhase)
    : null

  return (
    <div className="border-b bg-background">
      <div className="flex items-center justify-center gap-0 px-4 py-2">
        {data.phases.map((phase, idx) => {
          const completed = phase.steps.filter((s) => s.status === "completed").length
          const total = phase.steps.length

          return (
            <div key={phase.name} className="flex items-center">
              {idx > 0 && (
                <div
                  className={`h-0.5 w-8 md:w-16 ${getConnectorStyles(data.phases[idx - 1].status)}`}
                />
              )}

              <div className="flex flex-col items-center">
                <button
                  className={`w-7 h-7 rounded-full flex items-center justify-center cursor-pointer transition-colors ${getPhaseStyles(phase.status)} ${expandedPhase === phase.name ? "ring-2 ring-offset-1 ring-primary" : ""}`}
                  onClick={() => handlePhaseClick(phase)}
                >
                  <PhaseIcon status={phase.status} />
                </button>
                <span className="text-[11px] mt-0.5 whitespace-nowrap text-muted-foreground">
                  {phase.label} {completed}/{total}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {expandedData && (
        <div className="flex items-center justify-center gap-4 px-4 pb-2 border-t border-dashed">
          {expandedData.steps.map((step) => (
            <div key={step.name} className="flex items-center gap-1 py-1 text-xs">
              <StepIcon status={step.status} />
              <span className={step.status === "completed" ? "text-muted-foreground" : ""}>
                {step.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
