import { useState, useEffect, useCallback } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { APP_NAME } from "../lib/constants"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import {
  uploadProjects,
  uploadExperts,
  uploadGuests,
  getUploadJobStatus,
  getCurrentEvent,
  createEvent,
  updateCurrentEvent,
  isNoEventError,
  type Event,
  type EventCreateRequest,
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

function EventTab({ event, onEventChange }: { event: Event | null; onEventChange: () => void }) {
  const [name, setName] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const isEdit = !!event

  useEffect(() => {
    if (event) {
      setName(event.name || "")
      setStartDate(event.start_date || "")
      setEndDate(event.end_date || "")
      setDescription(event.description || "")
    }
  }, [event])

  const createMutation = useMutation({
    mutationFn: (body: EventCreateRequest) => createEvent(body),
    onSuccess: () => {
      setSuccess("Мероприятие создано")
      setError(null)
      onEventChange()
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setSuccess(null)
      const detail = err.response?.data?.detail
      setError(typeof detail === "string" ? detail : err.message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (body: Partial<{ name: string; start_date: string; end_date: string; description: string }>) =>
      updateCurrentEvent(body),
    onSuccess: () => {
      setSuccess("Изменения сохранены")
      setError(null)
      onEventChange()
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setSuccess(null)
      const detail = err.response?.data?.detail
      setError(typeof detail === "string" ? detail : err.message)
    },
  })

  const handleSubmit = () => {
    setError(null)
    setSuccess(null)

    if (!name.trim()) {
      setError("Введите название мероприятия")
      return
    }
    if (!startDate) {
      setError("Введите дату начала")
      return
    }
    if (!endDate) {
      setError("Введите дату окончания")
      return
    }
    if (endDate < startDate) {
      setError("Дата окончания не может быть раньше даты начала")
      return
    }

    if (isEdit) {
      updateMutation.mutate({ name, start_date: startDate, end_date: endDate, description: description || undefined })
    } else {
      createMutation.mutate({ name, start_date: startDate, end_date: endDate, description: description || undefined })
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Редактирование мероприятия" : "Создание мероприятия"}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="event-name">Название</Label>
          <Input
            id="event-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Demo Day 2026"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="event-start">Дата начала</Label>
            <Input
              id="event-start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="event-end">Дата окончания</Label>
            <Input
              id="event-end"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="event-desc">Описание</Label>
          <Input
            id="event-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Описание (необязательно)"
          />
        </div>

        <Button onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Сохранение..." : isEdit ? "Сохранить" : "Создать"}
        </Button>

        {error && <p className="text-sm text-red-500">{error}</p>}
        {success && <p className="text-sm text-green-600">{success}</p>}
      </CardContent>
    </Card>
  )
}

function NoEventHint({ onGoToEvent }: { onGoToEvent: () => void }) {
  return (
    <Card className="border-amber-300 bg-amber-50">
      <CardContent className="pt-6">
        <p className="text-sm text-amber-800">
          Сначала создайте мероприятие на вкладке «Событие»
        </p>
        <Button variant="link" className="px-0 text-amber-700" onClick={onGoToEvent}>
          Перейти к созданию мероприятия
        </Button>
      </CardContent>
    </Card>
  )
}

export function DataImport() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState("event")

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

  const handleEventChange = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["currentEvent"] })
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
  }, [queryClient])

  const refreshAllStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["projects"] })
  }, [queryClient])

  const goToEventTab = useCallback(() => setActiveTab("event"), [])

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

  // --- Guests ---
  const [guestFile, setGuestFile] = useState<File | null>(null)
  const [guestSubtype, setGuestSubtype] = useState<string>("")
  const [guestResult, setGuestResult] = useState<GuestUploadResult | null>(() =>
    loadFromStorage<GuestUploadResult>("import_guest_result")
  )
  const [guestConflict, setGuestConflict] = useState<GuestUploadConflict | null>(null)
  const [guestError, setGuestError] = useState<string | null>(null)

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

  useEffect(() => {
    saveToStorage("import_guest_result", guestResult)
  }, [guestResult])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Импорт данных</h2>

      <Tabs value={activeTab} onValueChange={setActiveTab} defaultValue="event">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="event">1. Событие</TabsTrigger>
          <TabsTrigger value="projects">2. Проекты</TabsTrigger>
          <TabsTrigger value="experts">3. Эксперты</TabsTrigger>
          <TabsTrigger value="guests">4. Гости</TabsTrigger>
        </TabsList>

        {/* Tab 1: Event */}
        <TabsContent value="event">
          <EventTab event={currentEvent ?? null} onEventChange={handleEventChange} />
        </TabsContent>

        {/* Tab 2: Projects */}
        <TabsContent value="projects">
          {!hasEvent ? (
            <NoEventHint onGoToEvent={goToEventTab} />
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
                  label="Перетащите CSV, JSON или XLSX файл с проектами"
                  disabled={!!isProjectJobRunning}
                />
                <details className="text-xs text-muted-foreground">
                  <summary className="cursor-pointer hover:text-foreground">Формат файла</summary>
                  <div className="mt-1 pl-3 space-y-1">
                    <p><strong>Обязательные поля:</strong> <code>title</code> (мин. 3 символа), <code>description</code> (макс. 2000), <code>author</code></p>
                    <p><strong>Необязательные:</strong> <code>telegram_contact</code>, <code>tags</code></p>
                    <p><strong>Алиасы:</strong> <code>название</code>/<code>проект</code> = title, <code>описание</code> = description, <code>автор</code>/<code>команда</code> = author, <code>теги</code>/<code>технологии</code> = tags</p>
                  </div>
                </details>

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

        {/* Tab 3: Experts */}
        <TabsContent value="experts">
          {!hasEvent ? (
            <NoEventHint onGoToEvent={goToEventTab} />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Эксперты</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setExpertFile}
                  label="Перетащите CSV, JSON или XLSX файл с экспертами"
                />
                <details className="text-xs text-muted-foreground">
                  <summary className="cursor-pointer hover:text-foreground">Формат файла</summary>
                  <div className="mt-1 pl-3 space-y-1">
                    <p><strong>Обязательные поля:</strong> <code>id</code>, <code>name</code></p>
                    <p><strong>Необязательные:</strong> <code>telegram</code>, <code>position</code>, <code>expertise_tags</code></p>
                  </div>
                </details>

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

        {/* Tab 4: Guests */}
        <TabsContent value="guests">
          {!hasEvent ? (
            <NoEventHint onGoToEvent={goToEventTab} />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Гости</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
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
                  accept=".csv,.json,.xlsx"
                  onFileSelect={setGuestFile}
                  label="Перетащите CSV, JSON или XLSX файл с гостями"
                />
                <details className="text-xs text-muted-foreground">
                  <summary className="cursor-pointer hover:text-foreground">Формат файла</summary>
                  <div className="mt-1 pl-3 space-y-1">
                    <p><strong>Обязательные поля:</strong> <code>name</code></p>
                    <p><strong>Необязательные:</strong> <code>telegram</code></p>
                  </div>
                </details>

                <Button
                  onClick={handleGuestUpload}
                  disabled={!guestFile || !guestSubtype || guestMutation.isPending}
                >
                  {guestMutation.isPending ? "Загрузка..." : "Загрузить"}
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
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
