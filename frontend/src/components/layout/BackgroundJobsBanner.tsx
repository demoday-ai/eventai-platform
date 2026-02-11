import { X, Loader2, CheckCircle2, XCircle, Sparkles } from "lucide-react"
import { useBackgroundJobs } from "../../contexts/BackgroundJobsContext"
import { Button } from "../ui/button"

export function BackgroundJobsBanner() {
  const { jobs, cancelJob, clearJob } = useBackgroundJobs()

  const activeJobs = jobs.filter(
    (job) => job.status !== "completed" && job.status !== "failed" && job.status !== "cancelled"
  )

  const completedJobs = jobs.filter(
    (job) => job.status === "completed" || job.status === "failed" || job.status === "cancelled"
  )

  if (jobs.length === 0) return null

  return (
    <div className="bg-background border-b">
      {activeJobs.map((job) => (
        <div key={job.id} className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1">
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-yellow-500" />
                <span className="font-medium">Генерация тегов</span>
                {job.progress && (
                  <span className="text-sm text-muted-foreground">
                    {job.progress.current} / {job.progress.total}
                  </span>
                )}
              </div>
              {job.progress && job.progress.total > 0 && (
                <div className="mt-2 w-full bg-secondary rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{
                      width: `${(job.progress.current / job.progress.total) * 100}%`,
                    }}
                  />
                </div>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => cancelJob(job.id)}
            className="text-muted-foreground hover:text-foreground"
          >
            Отменить
          </Button>
        </div>
      ))}

      {completedJobs.map((job) => (
        <div
          key={job.id}
          className={`px-4 py-3 flex items-center justify-between ${
            job.status === "completed"
              ? "bg-green-50 dark:bg-green-950"
              : job.status === "cancelled"
                ? "bg-yellow-50 dark:bg-yellow-950"
                : "bg-red-50 dark:bg-red-950"
          }`}
        >
          <div className="flex items-center gap-3 flex-1">
            {job.status === "completed" ? (
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            )}
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-yellow-500" />
                <span className="font-medium">
                  {job.status === "completed"
                    ? "Генерация тегов завершена"
                    : job.status === "cancelled"
                      ? "Генерация тегов отменена"
                      : "Ошибка генерации тегов"}
                </span>
              </div>
              {job.message && (
                <p className="text-sm text-muted-foreground mt-1">{job.message}</p>
              )}
              {job.error && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">{job.error}</p>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => clearJob(job.id)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
    </div>
  )
}
