import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Check, Circle, Loader2 } from "lucide-react"
import { usePipelineStatus } from "../../hooks/usePipelineStatus"
import type { PipelinePhase } from "../../lib/api-client"

const PHASE_LINKS: Record<string, string> = {
  data: "/import",
  distribution: "/clustering",
  launch: "/reminders",
}

function PhaseIcon({ status }: { status: PipelinePhase["status"] }) {
  if (status === "completed") {
    return <Check className="w-4 h-4 text-white" />
  }
  if (status === "in_progress") {
    return <Loader2 className="w-4 h-4 text-white animate-spin" />
  }
  return <Circle className="w-4 h-4 text-muted-foreground" />
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
  const navigate = useNavigate()
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null)

  if (!data) return null

  const handlePhaseClick = (phase: PipelinePhase) => {
    // Toggle sub-steps visibility
    if (expandedPhase === phase.name) {
      setExpandedPhase(null)
    } else {
      setExpandedPhase(phase.name)
    }
  }

  const handlePhaseNavigate = (phase: PipelinePhase) => {
    // Navigate to first incomplete step's page, or phase default
    const incompleteStep = phase.steps.find((s) => s.status === "not_started")
    if (incompleteStep) {
      // Find corresponding link from next_action or use phase default
      const link = data.next_action?.step === incompleteStep.name
        ? data.next_action.link
        : PHASE_LINKS[phase.name]
      navigate(link)
    } else {
      navigate(PHASE_LINKS[phase.name])
    }
  }

  return (
    <div className="border-b bg-background px-4 py-3">
      <div className="flex items-center justify-center gap-0">
        {data.phases.map((phase, idx) => (
          <div key={phase.name} className="flex items-center">
            {/* Connector line (before phase, except first) */}
            {idx > 0 && (
              <div
                className={`h-0.5 w-8 md:w-16 ${getConnectorStyles(data.phases[idx - 1].status)}`}
              />
            )}

            {/* Phase */}
            <div className="flex flex-col items-center relative">
              <button
                className={`w-8 h-8 rounded-full flex items-center justify-center cursor-pointer transition-colors ${getPhaseStyles(phase.status)}`}
                onClick={() => handlePhaseClick(phase)}
                onDoubleClick={() => handlePhaseNavigate(phase)}
                title={`${phase.label} — двойной клик для навигации`}
              >
                <PhaseIcon status={phase.status} />
              </button>
              <span className="text-xs mt-1 whitespace-nowrap">{phase.label}</span>

              {/* Expanded sub-steps */}
              {expandedPhase === phase.name && (
                <div className="absolute top-full mt-4 bg-popover border rounded-lg shadow-lg p-3 z-50 min-w-48">
                  <div className="space-y-2">
                    {phase.steps.map((step) => (
                      <div key={step.name} className="flex items-center gap-2 text-sm">
                        {step.status === "completed" ? (
                          <Check className="w-3.5 h-3.5 text-green-600 shrink-0" />
                        ) : (
                          <Circle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        )}
                        <span className={step.status === "completed" ? "text-muted-foreground" : ""}>
                          {step.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
