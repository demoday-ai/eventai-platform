import { useState, useEffect, useCallback } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Link } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { MergePreviewCard } from "../components/import/MergePreviewCard"
import { MergeResultCard } from "../components/import/MergeResult"
import { DeleteAllButton } from "../components/import/DeleteAllButton"
import { APP_NAME } from "../lib/constants"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs"
import {
  uploadProjects,
  uploadExperts,
  uploadGuests,
  getUploadJobStatus,
  getCurrentEvent,
  getDashboard,
  isNoEventError,
  previewProjectUpload,
  previewExpertUpload,
  previewGuestUpload,
  mergeProjects,
  mergeExperts,
  mergeGuests,
  deleteAllProjects,
  deleteAllExperts,
  deleteAllGuests,
  type UploadResult,
  type ExpertUploadResult,
  type GuestUploadResult,
  type MergePreview,
  type MergeApplyResult,
  type UploadJobResponse,
} from "../lib/api-client"

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

type MergeState = "idle" | "analyzing" | "preview" | "applying" | "result"

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

  const { data: dashboardData } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    enabled: hasEvent,
    retry: false,
  })

  const getGuestCount = (subtype: string) =>
    dashboardData?.guests?.by_subtype?.find((s) => s.subtype === subtype)?.count

  const refreshAllStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["projects"] })
    queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
  }, [queryClient])

  // ================================================================
  // PROJECTS TAB
  // ================================================================
  const [projectFile, setProjectFile] = useState<File | null>(null)
  const [projectMergeState, setProjectMergeState] = useState<MergeState>("idle")
  const [projectPreview, setProjectPreview] = useState<MergePreview | null>(null)
  const [projectMergeResult, setProjectMergeResult] = useState<MergeApplyResult | null>(null)
  // Legacy result (for replace all flow)
  const [projectResult, setProjectResult] = useState<UploadResult | null>(null)
  const [projectJobId, setProjectJobId] = useState<string | null>(null)
  const [projectJobStatus, setProjectJobStatus] = useState<string | null>(null)
  const [projectProgress, setProjectProgress] = useState<UploadJobResponse["progress"] | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null)

  // Job polling for both upload and merge
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
          // Check if this is a merge result or legacy upload result
          if ("added" in status.result) {
            setProjectMergeResult(status.result as unknown as MergeApplyResult)
            setProjectMergeState("result")
          } else {
            setProjectResult(status.result)
          }
          setProjectJobId(null)
          setProjectJobStatus(null)
          setProjectProgress(null)
          setProjectFile(null)
          setProjectPreview(null)
          refreshAllStats()
        } else if (status.status === "failed") {
          setProjectError(status.error || "Неизвестная ошибка")
          setProjectJobId(null)
          setProjectMergeState("idle")
        }
      } catch (err) {
        console.error("Failed to poll job status:", err)
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [projectJobId, projectJobStatus, refreshAllStats])

  const projectPreviewMutation = useMutation({
    mutationFn: (file: File) => previewProjectUpload(file),
    onSuccess: (data) => {
      setProjectPreview(data)
      setProjectMergeState("preview")
      setProjectError(null)
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      setProjectError(error.response?.data?.detail || error.message)
      setProjectMergeState("idle")
    },
  })

  const projectUploadMutation = useMutation({
    mutationFn: ({ file, replace }: { file: File; replace: boolean }) =>
      uploadProjects(file, replace),
    onSuccess: (data) => {
      if (data.job_id) {
        setProjectJobId(data.job_id)
        setProjectJobStatus(data.status)
        setProjectError(null)
        setProjectMergeState("applying")
      }
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      setProjectError(error.response?.data?.detail || error.message)
      setProjectMergeState("idle")
    },
  })

  const projectHasData = (dashboardData?.projects?.total ?? 0) > 0

  const handleProjectAction = () => {
    if (!projectFile) return
    setProjectResult(null)
    setProjectMergeResult(null)
    setProjectError(null)
    setDeleteMessage(null)
    if (projectHasData) {
      setProjectMergeState("analyzing")
      projectPreviewMutation.mutate(projectFile)
    } else {
      setProjectMergeState("applying")
      projectUploadMutation.mutate({ file: projectFile, replace: false })
    }
  }

  const handleProjectMergeApply = (addNew: boolean, updateExisting: boolean) => {
    if (!projectFile) return
    setProjectMergeState("applying")
    mergeProjects(projectFile, addNew, updateExisting)
      .then((data) => {
        if (data.job_id) {
          setProjectJobId(data.job_id)
          setProjectJobStatus(data.status)
        }
      })
      .catch((err) => {
        setProjectError(err.response?.data?.detail || err.message)
        setProjectMergeState("preview")
      })
  }

  const handleProjectReplaceAll = () => {
    if (!projectFile) return
    setProjectMergeState("applying")
    projectUploadMutation.mutate({ file: projectFile, replace: true })
  }

  const handleProjectCancelPreview = () => {
    setProjectPreview(null)
    setProjectMergeState("idle")
  }

  const isProjectBusy = projectJobId && (projectJobStatus === "pending" || projectJobStatus === "running")

  // ================================================================
  // EXPERTS TAB
  // ================================================================
  const [expertFile, setExpertFile] = useState<File | null>(null)
  const [expertMergeState, setExpertMergeState] = useState<MergeState>("idle")
  const [expertPreview, setExpertPreview] = useState<MergePreview | null>(null)
  const [expertMergeResult, setExpertMergeResult] = useState<MergeApplyResult | null>(null)
  const [expertResult, setExpertResult] = useState<ExpertUploadResult | null>(null)
  const [expertError, setExpertError] = useState<string | null>(null)

  const expertPreviewMutation = useMutation({
    mutationFn: (file: File) => previewExpertUpload(file),
    onSuccess: (data) => {
      setExpertPreview(data)
      setExpertMergeState("preview")
      setExpertError(null)
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      setExpertError(error.response?.data?.detail || error.message)
      setExpertMergeState("idle")
    },
  })

  const expertUploadMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadExperts(file, confirmReplace),
  })

  const expertHasData = (dashboardData?.experts?.total ?? 0) > 0

  const handleExpertAction = () => {
    if (!expertFile) return
    setExpertResult(null)
    setExpertMergeResult(null)
    setExpertError(null)
    setDeleteMessage(null)
    if (expertHasData) {
      setExpertMergeState("analyzing")
      expertPreviewMutation.mutate(expertFile)
    } else {
      setExpertMergeState("applying")
      expertUploadMutation.mutate(
        { file: expertFile, confirmReplace: false },
        {
          onSuccess: (data) => {
            if (!("existing_count" in data)) {
              setExpertResult(data)
              setExpertFile(null)
            }
            setExpertMergeState("idle")
            refreshAllStats()
          },
          onError: (error: Error) => {
            const axErr = error as AxiosError<{ detail: string }>
            setExpertError(axErr.response?.data?.detail || error.message)
            setExpertMergeState("idle")
          },
        },
      )
    }
  }

  const handleExpertMergeApply = async (addNew: boolean, updateExisting: boolean) => {
    if (!expertFile) return
    setExpertMergeState("applying")
    try {
      const result = await mergeExperts(expertFile, addNew, updateExisting)
      setExpertMergeResult(result)
      setExpertMergeState("result")
      setExpertPreview(null)
      setExpertFile(null)
      refreshAllStats()
    } catch (err) {
      const axErr = err as AxiosError<{ detail: string }>
      setExpertError(axErr.response?.data?.detail || axErr.message)
      setExpertMergeState("preview")
    }
  }

  const handleExpertReplaceAll = () => {
    if (!expertFile) return
    setExpertMergeState("applying")
    expertUploadMutation.mutate(
      { file: expertFile, confirmReplace: true },
      {
        onSuccess: (data) => {
          if ("existing_count" in data) {
            // Should not happen with confirmReplace=true, but handle gracefully
            setExpertError("Unexpected conflict response")
          } else {
            setExpertResult(data)
            setExpertPreview(null)
            setExpertFile(null)
            setExpertMergeState("idle")
            refreshAllStats()
          }
        },
        onError: (error: Error) => {
          const axErr = error as AxiosError<{ detail: string }>
          setExpertError(axErr.response?.data?.detail || error.message)
          setExpertMergeState("idle")
        },
      },
    )
  }

  const handleExpertCancelPreview = () => {
    setExpertPreview(null)
    setExpertMergeState("idle")
  }

  // ================================================================
  // STUDENTS TAB
  // ================================================================
  const [studentFile, setStudentFile] = useState<File | null>(null)
  const [studentMergeState, setStudentMergeState] = useState<MergeState>("idle")
  const [studentPreview, setStudentPreview] = useState<MergePreview | null>(null)
  const [studentMergeResult, setStudentMergeResult] = useState<MergeApplyResult | null>(null)
  const [studentResult, setStudentResult] = useState<GuestUploadResult | null>(null)
  const [studentError, setStudentError] = useState<string | null>(null)

  const studentPreviewMutation = useMutation({
    mutationFn: (file: File) => previewGuestUpload(file, "student"),
    onSuccess: (data) => {
      setStudentPreview(data)
      setStudentMergeState("preview")
      setStudentError(null)
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      setStudentError(error.response?.data?.detail || error.message)
      setStudentMergeState("idle")
    },
  })

  const studentUploadMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadGuests(file, "student", confirmReplace),
  })

  const studentHasData = (getGuestCount("student") ?? 0) > 0

  const handleStudentAction = () => {
    if (!studentFile) return
    setStudentResult(null)
    setStudentMergeResult(null)
    setStudentError(null)
    setDeleteMessage(null)
    if (studentHasData) {
      setStudentMergeState("analyzing")
      studentPreviewMutation.mutate(studentFile)
    } else {
      setStudentMergeState("applying")
      studentUploadMutation.mutate(
        { file: studentFile, confirmReplace: false },
        {
          onSuccess: (data) => {
            if (!("existing_count" in data)) {
              setStudentResult(data)
              setStudentFile(null)
            }
            setStudentMergeState("idle")
            refreshAllStats()
          },
          onError: (error: Error) => {
            const axErr = error as AxiosError<{ detail: string }>
            setStudentError(axErr.response?.data?.detail || error.message)
            setStudentMergeState("idle")
          },
        },
      )
    }
  }

  const handleStudentMergeApply = async (addNew: boolean, updateExisting: boolean) => {
    if (!studentFile) return
    setStudentMergeState("applying")
    try {
      const result = await mergeGuests(studentFile, "student", addNew, updateExisting)
      setStudentMergeResult(result)
      setStudentMergeState("result")
      setStudentPreview(null)
      setStudentFile(null)
      refreshAllStats()
    } catch (err) {
      const axErr = err as AxiosError<{ detail: string }>
      setStudentError(axErr.response?.data?.detail || axErr.message)
      setStudentMergeState("preview")
    }
  }

  const handleStudentReplaceAll = () => {
    if (!studentFile) return
    setStudentMergeState("applying")
    studentUploadMutation.mutate(
      { file: studentFile, confirmReplace: true },
      {
        onSuccess: (data) => {
          if ("existing_count" in data) {
            setStudentError("Unexpected conflict response")
          } else {
            setStudentResult(data)
            setStudentPreview(null)
            setStudentFile(null)
            setStudentMergeState("idle")
            refreshAllStats()
          }
        },
        onError: (error: Error) => {
          const axErr = error as AxiosError<{ detail: string }>
          setStudentError(axErr.response?.data?.detail || error.message)
          setStudentMergeState("idle")
        },
      },
    )
  }

  const handleStudentCancelPreview = () => {
    setStudentPreview(null)
    setStudentMergeState("idle")
  }

  // ================================================================
  // PARTNERS TAB
  // ================================================================
  const [partnerFile, setPartnerFile] = useState<File | null>(null)
  const [partnerMergeState, setPartnerMergeState] = useState<MergeState>("idle")
  const [partnerPreview, setPartnerPreview] = useState<MergePreview | null>(null)
  const [partnerMergeResult, setPartnerMergeResult] = useState<MergeApplyResult | null>(null)
  const [partnerResult, setPartnerResult] = useState<GuestUploadResult | null>(null)
  const [partnerError, setPartnerError] = useState<string | null>(null)

  const partnerPreviewMutation = useMutation({
    mutationFn: (file: File) => previewGuestUpload(file, "business_partner"),
    onSuccess: (data) => {
      setPartnerPreview(data)
      setPartnerMergeState("preview")
      setPartnerError(null)
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      setPartnerError(error.response?.data?.detail || error.message)
      setPartnerMergeState("idle")
    },
  })

  const partnerUploadMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadGuests(file, "business_partner", confirmReplace),
  })

  const partnerHasData = (dashboardData?.partners?.total ?? 0) > 0

  const handlePartnerAction = () => {
    if (!partnerFile) return
    setPartnerResult(null)
    setPartnerMergeResult(null)
    setPartnerError(null)
    setDeleteMessage(null)
    if (partnerHasData) {
      setPartnerMergeState("analyzing")
      partnerPreviewMutation.mutate(partnerFile)
    } else {
      setPartnerMergeState("applying")
      partnerUploadMutation.mutate(
        { file: partnerFile, confirmReplace: false },
        {
          onSuccess: (data) => {
            if (!("existing_count" in data)) {
              setPartnerResult(data)
              setPartnerFile(null)
            }
            setPartnerMergeState("idle")
            refreshAllStats()
          },
          onError: (error: Error) => {
            const axErr = error as AxiosError<{ detail: string }>
            setPartnerError(axErr.response?.data?.detail || error.message)
            setPartnerMergeState("idle")
          },
        },
      )
    }
  }

  const handlePartnerMergeApply = async (addNew: boolean, updateExisting: boolean) => {
    if (!partnerFile) return
    setPartnerMergeState("applying")
    try {
      const result = await mergeGuests(partnerFile, "business_partner", addNew, updateExisting)
      setPartnerMergeResult(result)
      setPartnerMergeState("result")
      setPartnerPreview(null)
      setPartnerFile(null)
      refreshAllStats()
    } catch (err) {
      const axErr = err as AxiosError<{ detail: string }>
      setPartnerError(axErr.response?.data?.detail || axErr.message)
      setPartnerMergeState("preview")
    }
  }

  const handlePartnerReplaceAll = () => {
    if (!partnerFile) return
    setPartnerMergeState("applying")
    partnerUploadMutation.mutate(
      { file: partnerFile, confirmReplace: true },
      {
        onSuccess: (data) => {
          if ("existing_count" in data) {
            setPartnerError("Unexpected conflict response")
          } else {
            setPartnerResult(data)
            setPartnerPreview(null)
            setPartnerFile(null)
            setPartnerMergeState("idle")
            refreshAllStats()
          }
        },
        onError: (error: Error) => {
          const axErr = error as AxiosError<{ detail: string }>
          setPartnerError(axErr.response?.data?.detail || error.message)
          setPartnerMergeState("idle")
        },
      },
    )
  }

  const handlePartnerCancelPreview = () => {
    setPartnerPreview(null)
    setPartnerMergeState("idle")
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Импорт данных</h2>

      {deleteMessage && (
        <Card className="border-green-300 bg-green-50">
          <CardContent className="pt-4">
            <p className="text-sm text-green-800">{deleteMessage}</p>
          </CardContent>
        </Card>
      )}

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
                <CardTitle className="flex items-center gap-2">
                  Проекты
                  {dashboardData?.projects?.total ? (
                    <span className="text-sm font-normal text-muted-foreground">
                      (загружено: {dashboardData.projects.total})
                    </span>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {isProjectBusy && (
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
                  disabled={!!isProjectBusy || projectMergeState === "analyzing"}
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["Название", "Описание", "Автор"]}
                  optionalColumns={["Телеграм", "Теги", "Трек"]}
                  templateUrl="/templates/projects_template.xlsx"
                />

                <Button
                  onClick={handleProjectAction}
                  disabled={!projectFile || projectPreviewMutation.isPending || !!isProjectBusy}
                >
                  {projectPreviewMutation.isPending ? "Анализ..."
                    : !!isProjectBusy ? "Загрузка..."
                    : projectHasData ? "Анализировать" : "Загрузить"}
                </Button>

                {projectError && (
                  <p className="text-sm text-red-500">Ошибка: {projectError}</p>
                )}

                {projectMergeState === "preview" && projectPreview && (
                  <MergePreviewCard
                    preview={projectPreview}
                    type="projects"
                    onApply={handleProjectMergeApply}
                    onReplaceAll={handleProjectReplaceAll}
                    onCancel={handleProjectCancelPreview}
                    isApplying={projectUploadMutation.isPending || !!isProjectBusy}
                  />
                )}

                {projectMergeResult && <MergeResultCard result={projectMergeResult} type="projects" />}
                {projectResult && <ImportSummary result={projectResult} type="projects" />}

                {/* Delete all */}
                <div className="pt-4 border-t">
                  <DeleteAllButton
                    label="всех проектов"
                    count={dashboardData?.projects?.total}
                    deleteFn={deleteAllProjects}
                    onDeleted={(n) => {
                      setDeleteMessage(`Удалено проектов: ${n}`)
                      setProjectResult(null)
                      setProjectMergeResult(null)
                      refreshAllStats()
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 2: Experts */}
        <TabsContent value="experts">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Эксперты
                  {dashboardData?.experts?.total ? (
                    <span className="text-sm font-normal text-muted-foreground">
                      (загружено: {dashboardData.experts.total})
                    </span>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setExpertFile}
                  label="Перетащите файл с экспертами или нажмите кнопку"
                  disabled={expertMergeState === "analyzing" || expertMergeState === "applying"}
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["ФИО"]}
                  optionalColumns={["Телеграм", "Описание", "Теги"]}
                  templateUrl="/templates/experts_template.xlsx"
                />

                <Button
                  onClick={handleExpertAction}
                  disabled={!expertFile || expertPreviewMutation.isPending || expertMergeState === "applying"}
                >
                  {expertPreviewMutation.isPending ? "Анализ..."
                    : expertMergeState === "applying" ? "Загрузка..."
                    : expertHasData ? "Анализировать" : "Загрузить"}
                </Button>

                {expertError && (
                  <p className="text-sm text-red-500">Ошибка: {expertError}</p>
                )}

                {expertMergeState === "preview" && expertPreview && (
                  <MergePreviewCard
                    preview={expertPreview}
                    type="experts"
                    onApply={handleExpertMergeApply}
                    onReplaceAll={handleExpertReplaceAll}
                    onCancel={handleExpertCancelPreview}
                    isApplying={expertUploadMutation.isPending}
                  />
                )}

                {expertMergeResult && <MergeResultCard result={expertMergeResult} type="experts" />}
                {expertResult && <ImportSummary result={expertResult} type="experts" />}

                <div className="pt-4 border-t">
                  <DeleteAllButton
                    label="всех экспертов"
                    count={dashboardData?.experts?.total}
                    deleteFn={deleteAllExperts}
                    onDeleted={(n) => {
                      setDeleteMessage(`Удалено экспертов: ${n}`)
                      setExpertResult(null)
                      setExpertMergeResult(null)
                      refreshAllStats()
                    }}
                  />
                </div>
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
                <CardTitle className="flex items-center gap-2">
                  Студенты
                  {getGuestCount("student") ? (
                    <span className="text-sm font-normal text-muted-foreground">
                      (загружено: {getGuestCount("student")})
                    </span>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setStudentFile}
                  label="Перетащите файл со студентами или нажмите кнопку"
                  disabled={studentMergeState === "analyzing" || studentMergeState === "applying"}
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["ФИО", "Телеграм"]}
                  templateUrl="/templates/students_template.xlsx"
                />

                <Button
                  onClick={handleStudentAction}
                  disabled={!studentFile || studentPreviewMutation.isPending || studentMergeState === "applying"}
                >
                  {studentPreviewMutation.isPending ? "Анализ..."
                    : studentMergeState === "applying" ? "Загрузка..."
                    : studentHasData ? "Анализировать" : "Загрузить"}
                </Button>

                {studentError && (
                  <p className="text-sm text-red-500">Ошибка: {studentError}</p>
                )}

                {studentMergeState === "preview" && studentPreview && (
                  <MergePreviewCard
                    preview={studentPreview}
                    type="students"
                    onApply={handleStudentMergeApply}
                    onReplaceAll={handleStudentReplaceAll}
                    onCancel={handleStudentCancelPreview}
                    isApplying={studentUploadMutation.isPending}
                  />
                )}

                {studentMergeResult && <MergeResultCard result={studentMergeResult} type="students" />}
                {studentResult && <ImportSummary result={studentResult} type="students" />}

                <div className="pt-4 border-t">
                  <DeleteAllButton
                    label="всех студентов"
                    count={getGuestCount("student")}
                    deleteFn={() => deleteAllGuests("student")}
                    onDeleted={(n) => {
                      setDeleteMessage(`Удалено студентов: ${n}`)
                      setStudentResult(null)
                      setStudentMergeResult(null)
                      refreshAllStats()
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 4: Partners */}
        <TabsContent value="partners">
          {!hasEvent ? (
            <NoEventHint />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Партнёры
                  {dashboardData?.partners?.total ? (
                    <span className="text-sm font-normal text-muted-foreground">
                      (загружено: {dashboardData.partners.total})
                    </span>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setPartnerFile}
                  label="Перетащите файл с партнёрами или нажмите кнопку"
                  disabled={partnerMergeState === "analyzing" || partnerMergeState === "applying"}
                  formats={["XLSX", "CSV", "JSON"]}
                  requiredColumns={["ФИО", "Телеграм"]}
                  templateUrl="/templates/partners_template.xlsx"
                />

                <Button
                  onClick={handlePartnerAction}
                  disabled={!partnerFile || partnerPreviewMutation.isPending || partnerMergeState === "applying"}
                >
                  {partnerPreviewMutation.isPending ? "Анализ..."
                    : partnerMergeState === "applying" ? "Загрузка..."
                    : partnerHasData ? "Анализировать" : "Загрузить"}
                </Button>

                {partnerError && (
                  <p className="text-sm text-red-500">Ошибка: {partnerError}</p>
                )}

                {partnerMergeState === "preview" && partnerPreview && (
                  <MergePreviewCard
                    preview={partnerPreview}
                    type="partners"
                    onApply={handlePartnerMergeApply}
                    onReplaceAll={handlePartnerReplaceAll}
                    onCancel={handlePartnerCancelPreview}
                    isApplying={partnerUploadMutation.isPending}
                  />
                )}

                {partnerMergeResult && <MergeResultCard result={partnerMergeResult} type="partners" />}
                {partnerResult && <ImportSummary result={partnerResult} type="partners" />}

                <div className="pt-4 border-t">
                  <DeleteAllButton
                    label="всех партнёров"
                    count={dashboardData?.partners?.total}
                    deleteFn={() => deleteAllGuests("business_partner")}
                    onDeleted={(n) => {
                      setDeleteMessage(`Удалено партнёров: ${n}`)
                      setPartnerResult(null)
                      setPartnerMergeResult(null)
                      refreshAllStats()
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
