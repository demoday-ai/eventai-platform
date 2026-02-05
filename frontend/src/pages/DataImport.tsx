import { useState, useEffect } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { APP_NAME } from "../lib/constants"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import {
  uploadProjects,
  uploadExperts,
  uploadGuests,
  getDashboard,
  getProjects,
  getUploadJobStatus,
  type UploadResult,
  type ExpertUploadResult,
  type GuestUploadResult,
  type GuestUploadConflict,
  type UploadConflict,
  type ExpertUploadConflict,
  type UploadJobResponse,
} from "../lib/api-client"

export function DataImport() {
  const queryClient = useQueryClient()

  useEffect(() => {
    document.title = `${APP_NAME} - Импорт данных`
  }, [])

  // Fetch current data stats
  const { data: dashboard, refetch: refetchDashboard, error: dashboardError, isLoading: dashboardLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    retry: false,
  })

  const { data: projects, refetch: refetchProjects, error: projectsError, isLoading: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => getProjects(),
    retry: false,
  })

  // Log errors for debugging
  useEffect(() => {
    if (projectsError) {
      console.error("Projects query error:", projectsError)
    }
    if (dashboardError) {
      console.error("Dashboard query error:", dashboardError)
    }
  }, [projectsError, dashboardError])

  const projectCount = projects?.length ?? 0
  const expertCount = dashboard?.experts?.total ?? 0
  const guestCount = dashboard?.guests?.total ?? 0

  const refreshAllStats = () => {
    refetchDashboard()
    refetchProjects()
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["projects"] })
  }

  // --- Projects ---
  const [projectFile, setProjectFile] = useState<File | null>(null)
  const [projectResult, setProjectResult] = useState<UploadResult | null>(null)
  const [projectConflict, setProjectConflict] = useState<UploadConflict | null>(null)
  const [projectJobId, setProjectJobId] = useState<string | null>(null)
  const [projectJobStatus, setProjectJobStatus] = useState<string | null>(null)
  const [projectProgress, setProjectProgress] = useState<UploadJobResponse["progress"] | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [lastProjectFileName, setLastProjectFileName] = useState<string | null>(null)

  // Poll project upload job status
  useEffect(() => {
    if (!projectJobId || projectJobStatus === "completed" || projectJobStatus === "failed") {
      return
    }

    const interval = setInterval(async () => {
      try {
        const status = await getUploadJobStatus(projectJobId)
        setProjectJobStatus(status.status)
        setProjectProgress(status.progress || null)

        if (status.status === "completed" && status.result) {
          setProjectResult(status.result)
          setProjectJobId(null)
          setProjectJobStatus(null)
          setProjectProgress(null)
          if (projectFile) {
            setLastProjectFileName(projectFile.name)
          }
          setProjectFile(null)
          refreshAllStats()
        } else if (status.status === "failed") {
          setProjectError(status.error || "Неизвестная ошибка")
          setProjectJobId(null)
        }
      } catch (err) {
        console.error("Failed to poll job status:", err)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [projectJobId, projectJobStatus])

  const projectMutation = useMutation({
    mutationFn: ({ file, replace }: { file: File; replace: boolean }) =>
      uploadProjects(file, replace),
    onSuccess: (data) => {
      if (data.job_id) {
        setProjectJobId(data.job_id)
        setProjectJobStatus(data.status)
        setProjectError(null)
        setProjectConflict(null)
      }
    },
    onError: (error: AxiosError<{ detail: UploadConflict | string | { message: string; errors: unknown[] } }>) => {
      const detail = error.response?.data?.detail
      if (error.response?.status === 409 && detail && typeof detail === "object" && "message" in detail) {
        setProjectConflict(detail as UploadConflict)
      } else if (detail) {
        if (typeof detail === "string") {
          setProjectError(detail)
        } else if ("message" in detail) {
          setProjectError(detail.message)
        } else {
          setProjectError(error.message)
        }
      } else {
        setProjectError(error.message)
      }
    },
  })

  const handleProjectUpload = () => {
    if (!projectFile) return
    setProjectResult(null)
    setProjectConflict(null)
    setProjectError(null)
    projectMutation.mutate({ file: projectFile, replace: false })
  }

  const handleProjectReplace = () => {
    if (!projectFile) return
    setProjectConflict(null)
    setProjectError(null)
    projectMutation.mutate({ file: projectFile, replace: true })
  }

  const isProjectJobRunning = projectJobId && (projectJobStatus === "pending" || projectJobStatus === "running")

  // --- Experts ---
  const [expertFile, setExpertFile] = useState<File | null>(null)
  const [expertResult, setExpertResult] = useState<ExpertUploadResult | null>(null)
  const [expertConflict, setExpertConflict] = useState<ExpertUploadConflict | null>(null)
  const [expertError, setExpertError] = useState<string | null>(null)
  const [lastExpertFileName, setLastExpertFileName] = useState<string | null>(null)

  const expertMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadExperts(file, confirmReplace),
    onSuccess: (data) => {
      if ("existing_count" in data) {
        setExpertConflict(data as unknown as ExpertUploadConflict)
        setExpertResult(null)
      } else {
        setExpertResult(data)
        setExpertConflict(null)
        if (expertFile) {
          setLastExpertFileName(expertFile.name)
        }
        setExpertFile(null)
        setExpertError(null)
        refreshAllStats()
      }
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      const detail = error.response?.data?.detail
      if (typeof detail === "string") {
        setExpertError(detail)
      } else {
        setExpertError(error.message)
      }
    },
  })

  const handleExpertUpload = () => {
    if (!expertFile) return
    setExpertResult(null)
    setExpertConflict(null)
    setExpertError(null)
    expertMutation.mutate({ file: expertFile, confirmReplace: false })
  }

  const handleExpertReplace = () => {
    if (!expertFile) return
    setExpertConflict(null)
    expertMutation.mutate({ file: expertFile, confirmReplace: true })
  }

  // --- Guests ---
  const [guestFile, setGuestFile] = useState<File | null>(null)
  const [guestSubtype, setGuestSubtype] = useState<string>("")
  const [guestResult, setGuestResult] = useState<GuestUploadResult | null>(null)
  const [guestConflict, setGuestConflict] = useState<GuestUploadConflict | null>(null)
  const [guestError, setGuestError] = useState<string | null>(null)
  const [lastGuestFileName, setLastGuestFileName] = useState<string | null>(null)

  const guestMutation = useMutation({
    mutationFn: ({ file, subtype, confirmReplace }: { file: File; subtype: string; confirmReplace: boolean }) =>
      uploadGuests(file, subtype, confirmReplace),
    onSuccess: (data) => {
      if ("existing_count" in data) {
        setGuestConflict(data as unknown as GuestUploadConflict)
        setGuestResult(null)
      } else {
        setGuestResult(data)
        setGuestConflict(null)
        if (guestFile) {
          setLastGuestFileName(guestFile.name)
        }
        setGuestFile(null)
        setGuestError(null)
        refreshAllStats()
      }
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      const detail = error.response?.data?.detail
      if (typeof detail === "string") {
        setGuestError(detail)
      } else {
        setGuestError(error.message)
      }
    },
  })

  const handleGuestUpload = () => {
    if (!guestFile || !guestSubtype) return
    setGuestResult(null)
    setGuestConflict(null)
    setGuestError(null)
    guestMutation.mutate({ file: guestFile, subtype: guestSubtype, confirmReplace: false })
  }

  const handleGuestReplace = () => {
    if (!guestFile || !guestSubtype) return
    setGuestConflict(null)
    guestMutation.mutate({ file: guestFile, subtype: guestSubtype, confirmReplace: true })
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Импорт данных</h2>

      {/* Projects Section */}
      <Card>
        <CardHeader>
          <CardTitle>Проекты</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current data status - always show */}
          {!isProjectJobRunning && (
            projectsLoading ? (
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
                <p className="text-sm text-gray-600">Загрузка данных...</p>
              </div>
            ) : projectsError ? (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  Ошибка загрузки данных: {(projectsError as AxiosError<{ detail: string }>)?.response?.data?.detail || "Неизвестная ошибка"}
                </p>
              </div>
            ) : projectCount > 0 ? (
              <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-800 font-medium">
                  Загружено проектов: {projectCount}
                  {lastProjectFileName && (
                    <span className="font-normal text-green-600"> ({lastProjectFileName})</span>
                  )}
                </p>
                <p className="text-xs text-green-600 mt-1">
                  Для замены загрузите новый файл
                </p>
              </div>
            ) : (
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
                <p className="text-sm text-gray-600">
                  Проекты не загружены
                </p>
              </div>
            )
          )}

          {/* Upload progress */}
          {isProjectJobRunning && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800 font-medium">
                {projectProgress?.stage === "deleting" && "Удаление старых данных..."}
                {projectProgress?.stage === "saving" && (
                  <>
                    Загрузка: {projectProgress.current}/{projectProgress.total}
                    {projectProgress.tags_generated !== undefined && projectProgress.tags_generated > 0 && (
                      <span className="ml-2 text-blue-600">
                        (тегов сгенерировано: {projectProgress.tags_generated})
                      </span>
                    )}
                  </>
                )}
                {!projectProgress?.stage && "Обработка..."}
              </p>
              <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: projectProgress?.total
                      ? `${(projectProgress.current / projectProgress.total) * 100}%`
                      : "0%",
                  }}
                />
              </div>
            </div>
          )}

          <FileUpload
            accept=".csv,.json"
            onFileSelect={setProjectFile}
            label="Перетащите CSV или JSON файл с проектами"
            disabled={!!isProjectJobRunning}
          />

          <Button
            onClick={handleProjectUpload}
            disabled={!projectFile || projectMutation.isPending || !!isProjectJobRunning}
          >
            {isProjectJobRunning
              ? "Загрузка..."
              : projectMutation.isPending
              ? "Запуск..."
              : projectCount > 0
              ? "Заменить"
              : "Загрузить"}
          </Button>

          {projectConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{projectConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleProjectReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setProjectConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {(projectMutation.isError || projectError) && !projectConflict && (
            <p className="text-sm text-red-500">
              Ошибка загрузки: {projectError || (projectMutation.error instanceof Error ? projectMutation.error.message : "Неизвестная ошибка")}
            </p>
          )}

          {projectResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{projectResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {projectResult && <ImportSummary result={projectResult} type="projects" />}
        </CardContent>
      </Card>

      {/* Experts Section */}
      <Card>
        <CardHeader>
          <CardTitle>Эксперты</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current data status - always show */}
          {dashboardLoading ? (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-sm text-gray-600">Загрузка данных...</p>
            </div>
          ) : dashboardError ? (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">
                Ошибка загрузки данных: {(dashboardError as AxiosError<{ detail: string }>)?.response?.data?.detail || "Неизвестная ошибка"}
              </p>
            </div>
          ) : expertCount > 0 ? (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800 font-medium">
                Загружено экспертов: {expertCount}
                {lastExpertFileName && (
                  <span className="font-normal text-green-600"> ({lastExpertFileName})</span>
                )}
              </p>
              <p className="text-xs text-green-600 mt-1">
                Для замены загрузите новый файл
              </p>
            </div>
          ) : (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-sm text-gray-600">
                Эксперты не загружены
              </p>
            </div>
          )}

          <FileUpload
            accept=".csv,.json"
            onFileSelect={setExpertFile}
            label="Перетащите CSV или JSON файл с экспертами"
          />

          <Button
            onClick={handleExpertUpload}
            disabled={!expertFile || expertMutation.isPending}
          >
            {expertMutation.isPending ? "Загрузка..." : expertCount > 0 ? "Заменить" : "Загрузить"}
          </Button>

          {expertConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{expertConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleExpertReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpertConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {(expertMutation.isError || expertError) && (
            <p className="text-sm text-red-500">
              Ошибка загрузки: {expertError || "Неизвестная ошибка"}
            </p>
          )}

          {expertResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{expertResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {expertResult && <ImportSummary result={expertResult} type="experts" />}
        </CardContent>
      </Card>

      {/* Guests Section */}
      <Card>
        <CardHeader>
          <CardTitle>Гости</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current data status - always show */}
          {dashboardLoading ? (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-sm text-gray-600">Загрузка данных...</p>
            </div>
          ) : dashboardError ? (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">
                Ошибка загрузки данных: {(dashboardError as AxiosError<{ detail: string }>)?.response?.data?.detail || "Неизвестная ошибка"}
              </p>
            </div>
          ) : guestCount > 0 ? (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800 font-medium">
                Загружено гостей: {guestCount}
                {lastGuestFileName && (
                  <span className="font-normal text-green-600"> ({lastGuestFileName})</span>
                )}
              </p>
              {dashboard?.guests?.by_subtype && dashboard.guests.by_subtype.length > 0 && (
                <p className="text-xs text-green-600 mt-1">
                  {dashboard.guests.by_subtype.map(s => `${s.subtype}: ${s.count}`).join(", ")}
                </p>
              )}
            </div>
          ) : (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-sm text-gray-600">
                Гости не загружены
              </p>
            </div>
          )}

          <div>
            <label htmlFor="guest-subtype" className="text-sm font-medium mb-1 block">
              Тип гостя
            </label>
            <Select value={guestSubtype} onValueChange={setGuestSubtype}>
              <SelectTrigger id="guest-subtype">
                <SelectValue placeholder="Выберите тип" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="investor">Инвестор</SelectItem>
                <SelectItem value="business_partner">Бизнес-партнёр</SelectItem>
                <SelectItem value="mentor">Ментор</SelectItem>
                <SelectItem value="hr">HR</SelectItem>
                <SelectItem value="jury">Жюри</SelectItem>
                <SelectItem value="student">Студент</SelectItem>
                <SelectItem value="applicant">Абитуриент</SelectItem>
                <SelectItem value="other">Другое</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <FileUpload
            accept=".csv,.json"
            onFileSelect={setGuestFile}
            label="Перетащите CSV или JSON файл с гостями"
          />

          <Button
            onClick={handleGuestUpload}
            disabled={!guestFile || !guestSubtype || guestMutation.isPending}
          >
            {guestMutation.isPending ? "Загрузка..." : guestCount > 0 ? "Добавить" : "Загрузить"}
          </Button>

          {guestConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{guestConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleGuestReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setGuestConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {(guestMutation.isError || guestError) && (
            <p className="text-sm text-red-500">
              Ошибка загрузки: {guestError || "Неизвестная ошибка"}
            </p>
          )}

          {guestResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{guestResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {guestResult && <ImportSummary result={guestResult} type="guests" />}
        </CardContent>
      </Card>
    </div>
  )
}
