import { useState, useEffect, useCallback } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Link } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { APP_NAME } from "../lib/constants"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs"
import {
  uploadProjects,
  uploadExperts,
  uploadGuests,
  getUploadJobStatus,
  getCurrentEvent,
  isNoEventError,
  type UploadResult,
  type ExpertUploadResult,
  type GuestUploadResult,
  type GuestUploadConflict,
  type UploadConflict,
  type ExpertUploadConflict,
  type UploadJobResponse,
} from "../lib/api-client"

// Helper to load from localStorage
function loadFromStorage<T>(key: string): T | null {
  try {
    const stored = localStorage.getItem(key)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

// Helper to save to localStorage
function saveToStorage<T>(key: string, value: T | null) {
  if (value) {
    localStorage.setItem(key, JSON.stringify(value))
  } else {
    localStorage.removeItem(key)
  }
}

function NoEventHint() {
  return (
    <Card className="border-amber-300 bg-amber-50">
      <CardContent className="pt-6">
        <p className="text-sm text-amber-800">
          Сначала создайте мероприятие на странице «Мероприятие»
        </p>
        <Link to="/event">
          <Button variant="link" className="px-0 text-amber-700">
            Перейти к созданию мероприятия
          </Button>
        </Link>
      </CardContent>
    </Card>
  )
}

export function DataImport() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState("projects")

  useEffect(() => {
    document.title = `${APP_NAME} - Импорт данных`
  }, [])

  const { data: currentEvent } = useQuery({
    queryKey: ["currentEvent"],
    queryFn: getCurrentEvent,
    retry: (failureCount, error) => {
      if (isNoEventError(error)) return false
      return failureCount < 2
    },
  })

  const hasEvent = !!currentEvent

  const refreshAllStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["projects"] })
  }, [queryClient])

  // --- Projects ---
  const [projectFile, setProjectFile] = useState<File | null>(null)
  const [projectResult, setProjectResult] = useState<UploadResult | null>(() =>
    loadFromStorage<UploadResult>("import_project_result")
  )
  const [projectConflict, setProjectConflict] = useState<UploadConflict | null>(null)
  const [projectJobId, setProjectJobId] = useState<string | null>(null)
  const [projectJobStatus, setProjectJobStatus] = useState<string | null>(null)
  const [projectProgress, setProjectProgress] = useState<UploadJobResponse["progress"] | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)

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
  }, [projectJobId, projectJobStatus, refreshAllStats])

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

  useEffect(() => {
    saveToStorage("import_project_result", projectResult)
  }, [projectResult])

  // --- Experts ---
  const [expertFile, setExpertFile] = useState<File | null>(null)
  const [expertResult, setExpertResult] = useState<ExpertUploadResult | null>(() =>
    loadFromStorage<ExpertUploadResult>("import_expert_result")
  )
  const [expertConflict, setExpertConflict] = useState<ExpertUploadConflict | null>(null)
  const [expertError, setExpertError] = useState<string | null>(null)

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

  useEffect(() => {
    saveToStorage("import_expert_result", expertResult)
  }, [expertResult])

  // --- Students ---
  const [studentFile, setStudentFile] = useState<File | null>(null)
  const [studentResult, setStudentResult] = useState<GuestUploadResult | null>(() =>
    loadFromStorage<GuestUploadResult>("import_student_result")
  )
  const [studentConflict, setStudentConflict] = useState<GuestUploadConflict | null>(null)
  const [studentError, setStudentError] = useState<string | null>(null)

  const studentMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadGuests(file, "student", confirmReplace),
    onSuccess: (data) => {
      if ("existing_count" in data) {
        setStudentConflict(data as unknown as GuestUploadConflict)
        setStudentResult(null)
      } else {
        setStudentResult(data)
        setStudentConflict(null)
        setStudentFile(null)
        setStudentError(null)
        refreshAllStats()
      }
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      const detail = error.response?.data?.detail
      if (typeof detail === "string") {
        setStudentError(detail)
      } else {
        setStudentError(error.message)
      }
    },
  })

  const handleStudentUpload = () => {
    if (!studentFile) return
    setStudentResult(null)
    setStudentConflict(null)
    setStudentError(null)
    studentMutation.mutate({ file: studentFile, confirmReplace: false })
  }

  const handleStudentReplace = () => {
    if (!studentFile) return
    setStudentConflict(null)
    studentMutation.mutate({ file: studentFile, confirmReplace: true })
  }

  useEffect(() => {
    saveToStorage("import_student_result", studentResult)
  }, [studentResult])

  // --- Partners ---
  const [partnerFile, setPartnerFile] = useState<File | null>(null)
  const [partnerResult, setPartnerResult] = useState<GuestUploadResult | null>(() =>
    loadFromStorage<GuestUploadResult>("import_partner_result")
  )
  const [partnerConflict, setPartnerConflict] = useState<GuestUploadConflict | null>(null)
  const [partnerError, setPartnerError] = useState<string | null>(null)

  const partnerMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadGuests(file, "business_partner", confirmReplace),
    onSuccess: (data) => {
      if ("existing_count" in data) {
        setPartnerConflict(data as unknown as GuestUploadConflict)
        setPartnerResult(null)
      } else {
        setPartnerResult(data)
        setPartnerConflict(null)
        setPartnerFile(null)
        setPartnerError(null)
        refreshAllStats()
      }
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      const detail = error.response?.data?.detail
      if (typeof detail === "string") {
        setPartnerError(detail)
      } else {
        setPartnerError(error.message)
      }
    },
  })

  const handlePartnerUpload = () => {
    if (!partnerFile) return
    setPartnerResult(null)
    setPartnerConflict(null)
    setPartnerError(null)
    partnerMutation.mutate({ file: partnerFile, confirmReplace: false })
  }

  const handlePartnerReplace = () => {
    if (!partnerFile) return
    setPartnerConflict(null)
    partnerMutation.mutate({ file: partnerFile, confirmReplace: true })
  }

  useEffect(() => {
    saveToStorage("import_partner_result", partnerResult)
  }, [partnerResult])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Импорт данных</h2>

      <Tabs value={activeTab} onValueChange={setActiveTab} defaultValue="projects">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="projects">Проекты</TabsTrigger>
          <TabsTrigger value="students">Студенты</TabsTrigger>
          <TabsTrigger value="experts">Эксперты</TabsTrigger>
          <TabsTrigger value="partners">Партнёры</TabsTrigger>
        </TabsList>

        {/* Tab 1: Projects */}
        <TabsContent value="projects">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Проекты</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
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
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setProjectFile}
                  label="Перетащите файл с проектами или нажмите кнопку"
                  disabled={!!isProjectJobRunning}
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["title", "description", "author"]}
                  optionalColumns={["telegram_contact", "tags"]}
                  templateUrl="/templates/projects_template.xlsx"
                />

                <Button
                  onClick={handleProjectUpload}
                  disabled={!projectFile || projectMutation.isPending || !!isProjectJobRunning}
                >
                  {isProjectJobRunning
                    ? "Загрузка..."
                    : projectMutation.isPending
                    ? "Запуск..."
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
          )}
        </TabsContent>

        {/* Tab 4: Experts */}
        <TabsContent value="experts">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Эксперты</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setExpertFile}
                  label="Перетащите файл с экспертами или нажмите кнопку"
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["name"]}
                  optionalColumns={["telegram", "position", "expertise_tags"]}
                  templateUrl="/templates/experts_template.xlsx"
                />

                <Button
                  onClick={handleExpertUpload}
                  disabled={!expertFile || expertMutation.isPending}
                >
                  {expertMutation.isPending ? "Загрузка..." : "Загрузить"}
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
          )}
        </TabsContent>

        {/* Tab 3: Students */}
        <TabsContent value="students">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Студенты</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setStudentFile}
                  label="Перетащите файл со студентами или нажмите кнопку"
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["name", "telegram"]}
                  templateUrl="/templates/students_template.xlsx"
                />

                <Button
                  onClick={handleStudentUpload}
                  disabled={!studentFile || studentMutation.isPending}
                >
                  {studentMutation.isPending ? "Загрузка..." : "Загрузить"}
                </Button>

                {studentConflict && (
                  <Card className="border-yellow-300 bg-yellow-50">
                    <CardContent className="pt-4 space-y-3">
                      <p className="text-sm">{studentConflict.message}</p>
                      <div className="flex gap-2">
                        <Button variant="destructive" size="sm" onClick={handleStudentReplace}>
                          Заменить
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setStudentConflict(null)}
                        >
                          Отмена
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {(studentMutation.isError || studentError) && (
                  <p className="text-sm text-red-500">
                    Ошибка загрузки: {studentError || "Неизвестная ошибка"}
                  </p>
                )}

                {studentResult?.duplicate_warning && (
                  <Card className="border-amber-400 bg-amber-50">
                    <CardContent className="pt-4">
                      <p className="text-sm text-amber-800">{studentResult.duplicate_warning}</p>
                    </CardContent>
                  </Card>
                )}

                {studentResult && <ImportSummary result={studentResult} type="guests" />}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 5: Partners */}
        <TabsContent value="partners">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Партнёры</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setPartnerFile}
                  label="Перетащите файл с партнёрами или нажмите кнопку"
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["name", "telegram"]}
                  templateUrl="/templates/partners_template.xlsx"
                />

                <Button
                  onClick={handlePartnerUpload}
                  disabled={!partnerFile || partnerMutation.isPending}
                >
                  {partnerMutation.isPending ? "Загрузка..." : "Загрузить"}
                </Button>

                {partnerConflict && (
                  <Card className="border-yellow-300 bg-yellow-50">
                    <CardContent className="pt-4 space-y-3">
                      <p className="text-sm">{partnerConflict.message}</p>
                      <div className="flex gap-2">
                        <Button variant="destructive" size="sm" onClick={handlePartnerReplace}>
                          Заменить
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPartnerConflict(null)}
                        >
                          Отмена
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {(partnerMutation.isError || partnerError) && (
                  <p className="text-sm text-red-500">
                    Ошибка загрузки: {partnerError || "Неизвестная ошибка"}
                  </p>
                )}

                {partnerResult?.duplicate_warning && (
                  <Card className="border-amber-400 bg-amber-50">
                    <CardContent className="pt-4">
                      <p className="text-sm text-amber-800">{partnerResult.duplicate_warning}</p>
                    </CardContent>
                  </Card>
                )}

                {partnerResult && <ImportSummary result={partnerResult} type="guests" />}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
