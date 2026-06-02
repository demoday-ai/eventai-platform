import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from "react"
import { getTagGenerationStatus, cancelTagGeneration, type TagGenerationStatus } from "../lib/api-client"

interface BackgroundJob {
  id: string
  type: "tag-generation"
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  progress?: {
    current: number
    total: number
  }
  message?: string
  error?: string
}

interface BackgroundJobsContextValue {
  jobs: BackgroundJob[]
  startTagGeneration: (taskId: string) => void
  cancelJob: (jobId: string) => Promise<void>
  clearJob: (jobId: string) => void
}

const BackgroundJobsContext = createContext<BackgroundJobsContextValue | null>(null)

export function useBackgroundJobs() {
  const context = useContext(BackgroundJobsContext)
  if (!context) {
    throw new Error("useBackgroundJobs must be used within BackgroundJobsProvider")
  }
  return context
}

interface BackgroundJobsProviderProps {
  children: ReactNode
}

export function BackgroundJobsProvider({ children }: BackgroundJobsProviderProps) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([])
  const jobsRef = useRef<BackgroundJob[]>([])

  // Keep a live reference so the polling loop never reads a stale snapshot.
  useEffect(() => {
    jobsRef.current = jobs
  }, [jobs])

  // Single stable polling loop for the provider lifetime. Reads the current
  // job list via ref (not a closure), so progress updates and completion are
  // tracked correctly without tearing down/recreating the interval each tick.
  useEffect(() => {
    const interval = setInterval(async () => {
      const activeJobs = jobsRef.current.filter(
        (j) => j.status === "running" || j.status === "pending"
      )
      if (activeJobs.length === 0) return

      for (const job of activeJobs) {
        try {
          if (job.type === "tag-generation") {
            const status: TagGenerationStatus = await getTagGenerationStatus(job.id)

            setJobs((prev) =>
              prev.map((j) =>
                j.id === job.id
                  ? {
                      ...j,
                      status: status.status as BackgroundJob["status"],
                      progress: {
                        current: status.current,
                        total: status.total,
                      },
                      message:
                        status.status === "completed"
                          ? `Обработано: ${status.processed}, теги присвоены: ${status.tagged}`
                          : undefined,
                      error: status.error,
                    }
                  : j
              )
            )
          }
        } catch (error) {
          console.error("Failed to poll job status:", error)
        }
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  const startTagGeneration = (taskId: string) => {
    setJobs((prev) => [
      ...prev,
      {
        id: taskId,
        type: "tag-generation",
        status: "pending",
      },
    ])
  }

  const cancelJob = async (jobId: string) => {
    const job = jobs.find((j) => j.id === jobId)
    if (!job) return

    try {
      if (job.type === "tag-generation") {
        await cancelTagGeneration(jobId)
        setJobs((prev) =>
          prev.map((j) =>
            j.id === jobId
              ? { ...j, status: "cancelled", error: "Отменено пользователем" }
              : j
          )
        )
      }
    } catch (error) {
      console.error("Failed to cancel job:", error)
    }
  }

  const clearJob = (jobId: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== jobId))
  }

  return (
    <BackgroundJobsContext.Provider
      value={{ jobs, startTagGeneration, cancelJob, clearJob }}
    >
      {children}
    </BackgroundJobsContext.Provider>
  )
}
