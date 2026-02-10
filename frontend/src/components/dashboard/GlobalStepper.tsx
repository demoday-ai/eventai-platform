import { useState, useEffect, useRef } from "react"
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
  const containerRef = useRef<HTMLDivElement>(null)

  // Close popup on click outside
  useEffect(() => {
    if (!expandedPhase) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setExpandedPhase(null)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [expandedPhase])

  if (!data) return null

  const handlePhaseClick = (phase: PipelinePhase) => {
    if (expandedPhase === phase.name) {
      setExpandedPhase(null)
    } else {
      setExpandedPhase(phase.name)
    }
  }

  return (
    <div ref={containerRef} className="border-b bg-background px-4 py-2">
      <div className="flex items-center justify-center gap-0">
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

              <div className="flex flex-col items-center relative">
                <button
                  className={`w-7 h-7 rounded-full flex items-center justify-center cursor-pointer transition-colors ${getPhaseStyles(phase.status)}`}
                  onClick={() => handlePhaseClick(phase)}
                >
                  <PhaseIcon status={phase.status} />
                </button>
                <span className="text-[11px] mt-0.5 whitespace-nowrap text-muted-foreground">
                  {phase.label} {completed}/{total}
                </span>

                {expandedPhase === phase.name && (
                  <div className="absolute top-full mt-2 bg-popover border rounded-md shadow-md py-1.5 px-2 z-50 min-w-36">
                    {phase.steps.map((step) => (
                      <div key={step.name} className="flex items-center gap-1.5 py-0.5 text-xs">
                        {step.status === "completed" ? (
                          <Check className="w-3 h-3 text-green-600 shrink-0" />
                        ) : (
                          <Circle className="w-3 h-3 text-muted-foreground shrink-0" />
                        )}
                        <span className={step.status === "completed" ? "text-muted-foreground" : ""}>
                          {step.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
