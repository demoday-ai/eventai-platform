import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Layers } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Stepper } from "../components/ui/stepper"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import {
  runClustering,
  getClusteringJobStatus,
  getCurrentClustering,
  getProjects,
  moveProject,
  approveClustering,
  type ClusteringResult,
  type ClusteringRoom,
} from "../lib/api-client"

const STEPS = ["Параметры", "Результат", "Перемещение", "Одобрение"]

export function Clustering() {
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(0)
  const [numRooms, setNumRooms] = useState(6)
  const [feedback, setFeedback] = useState("")
  const [roomThemesInput, setRoomThemesInput] = useState("")
  const [roomThemesError, setRoomThemesError] = useState("")
  const [moveDialog, setMoveDialog] = useState<{
    projectId: string
    projectTitle: string
    sourceRoomId: string
  } | null>(null)

  // Background job state
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<string | null>(null)
  const [jobError, setJobError] = useState<string | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Кластеризация`
  }, [])

  // Check if projects exist
  const { data: projectsData, isFetched: projectsFetched } = useQuery({
    queryKey: ["projects", {}],
    queryFn: () => getProjects({}),
    retry: false,
  })

  // Try to load existing clustering
  const { data: existingClustering } = useQuery({
    queryKey: ["clustering"],
    queryFn: getCurrentClustering,
    retry: false,
  })

  const [clusteringResult, setClusteringResult] = useState<ClusteringResult | null>(null)

  // If existing clustering is loaded, jump to appropriate step
  useEffect(() => {
    if (existingClustering && !clusteringResult) {
      setClusteringResult(existingClustering)
      if (existingClustering.approved_at) {
        setCurrentStep(3)
      } else {
        setCurrentStep(1)
      }
    }
  }, [existingClustering, clusteringResult])

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus === "completed" || jobStatus === "failed") {
      return
    }

    const interval = setInterval(async () => {
      try {
        const status = await getClusteringJobStatus(jobId)
        setJobStatus(status.status)

        if (status.status === "completed" && status.result?.run_id) {
          // Fetch the actual clustering result
          const result = await getCurrentClustering()
          setClusteringResult(result)
          setJobId(null)
          setJobStatus(null)
          setFeedback("")
          setCurrentStep(1)
          queryClient.invalidateQueries({ queryKey: ["clustering"] })
        } else if (status.status === "failed") {
          setJobError(status.error || "Неизвестная ошибка")
          setJobId(null)
        }
      } catch (err) {
        console.error("Failed to poll job status:", err)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [jobId, jobStatus, queryClient])

  const parseRoomThemes = (raw: string) =>
    raw
      .split(/\n+/g)
      .map((item) => item.trim())
      .filter(Boolean)

  const runMutation = useMutation({
    mutationFn: (params: { roomThemes: string[] | null }) =>
      runClustering({
        num_rooms: numRooms,
        feedback: feedback || null,
        room_themes: params.roomThemes,
      }),
    onSuccess: (data) => {
      setJobId(data.job_id)
      setJobStatus(data.status)
      setJobError(null)
    },
    onError: (err) => {
      setJobError(err instanceof Error ? err.message : "Неизвестная ошибка")
    },
  })

  const moveMutation = useMutation({
    mutationFn: ({
      runId,
      projectId,
      targetRoomId,
    }: {
      runId: string
      projectId: string
      targetRoomId: string
    }) => moveProject(runId, { project_id: projectId, target_room_id: targetRoomId }),
    onSuccess: (data) => {
      setClusteringResult(data)
      setMoveDialog(null)
      queryClient.invalidateQueries({ queryKey: ["clustering"] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: (runId: string) => approveClustering(runId),
    onSuccess: () => {
      if (clusteringResult) {
        setClusteringResult({ ...clusteringResult, approved_at: new Date().toISOString() })
      }
      queryClient.invalidateQueries({ queryKey: ["clustering"] })
    },
  })

  const isApproved = !!clusteringResult?.approved_at
  const isJobRunning = jobId && (jobStatus === "pending" || jobStatus === "running")
  const handleRun = () => {
    const themes = parseRoomThemes(roomThemesInput)
    if (themes.length > 0 && themes.length !== numRooms) {
      setRoomThemesError(
        `Количество тем (${themes.length}) должно совпадать с числом залов (${numRooms}).`
      )
      return
    }
    setRoomThemesError("")
    runMutation.mutate({ roomThemes: themes.length > 0 ? themes : null })
  }

  const hasNoProjects = projectsFetched && projectsData && projectsData.length === 0 && !existingClustering

  if (hasNoProjects) {
    return (
      <div className="grid gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Кластеризация</h2>
        </div>
        <PageEmptyState
          icon={Layers}
          title="Для кластеризации необходимы проекты"
          description="Загрузите проекты на странице Импорта."
          actionLabel="Перейти к импорту"
          actionLink="/import"
        />
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Кластеризация</h2>
      </div>

      <Stepper steps={STEPS} currentStep={currentStep} />

      {/* Step 0: Parameters */}
      {currentStep === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Параметры кластеризации</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="num-rooms">Количество залов (2-20)</Label>
              <Input
                id="num-rooms"
                type="number"
                min={2}
                max={20}
                value={numRooms}
                onChange={(e) => {
                  setNumRooms(Number(e.target.value))
                  setRoomThemesError("")
                }}
                disabled={!!isJobRunning}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="feedback">Обратная связь (необязательно)</Label>
              <textarea
                id="feedback"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="Пожелания к кластеризации..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                disabled={!!isJobRunning}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="room-themes">Тематики залов (опционально)</Label>
              <textarea
                id="room-themes"
                className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder={"По одному на строке. Например:\nAI в медицине\nФинтех\nEdTech"}
                value={roomThemesInput}
                onChange={(e) => {
                  setRoomThemesInput(e.target.value)
                  setRoomThemesError("")
                }}
                disabled={!!isJobRunning}
              />
              <p className="text-xs text-muted-foreground">
                Если заполнено — количество тем должно совпадать с числом залов.
              </p>
              {roomThemesError && (
                <p className="text-sm text-red-500">{roomThemesError}</p>
              )}
            </div>
            <Button
              onClick={handleRun}
              disabled={runMutation.isPending || !!isJobRunning}
              className="w-full sm:w-auto"
            >
              {isJobRunning ? "Кластеризация..." : runMutation.isPending ? "Запуск..." : "Запустить"}
            </Button>

            {/* Job status indicator */}
            {isJobRunning && (
              <div className="p-3 bg-blue-50 rounded-md">
                <p className="text-sm text-blue-800">
                  Кластеризация выполняется... Статус: {jobStatus}
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  Это может занять несколько минут. Не закрывайте страницу.
                </p>
              </div>
            )}

            {jobError && (
              <p className="text-sm text-red-500">
                Ошибка: {jobError}
              </p>
            )}

            {clusteringResult && !isJobRunning && (
              <Button variant="outline" onClick={() => setCurrentStep(1)}>Далее</Button>
            )}

            {runMutation.isError && !jobError && (
              <p className="text-sm text-red-500">
                Ошибка: {runMutation.error instanceof Error ? runMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 1: Results */}
      {currentStep === 1 && clusteringResult && (
        <div className="space-y-4">
          <RoomsGrid rooms={clusteringResult.rooms} />
          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={() => setCurrentStep(2)} className="w-full sm:w-auto">Далее</Button>
            <Button
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => setCurrentStep(0)}
            >
              Назад
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Move projects */}
      {currentStep === 2 && clusteringResult && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Нажмите &quot;Переместить&quot; рядом с проектом, чтобы перенести его в другой зал.
          </p>
          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {clusteringResult.rooms.map((room) => (
              <Card key={room.id}>
                <CardHeader>
                  <CardTitle className="text-base">{room.name}</CardTitle>
                  <p className="text-xs text-muted-foreground">{room.theme_rationale}</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {room.projects.map((p) => (
                      <div key={p.id} className="flex items-center justify-between text-sm border rounded px-2 py-1">
                        <span className="truncate flex-1 mr-2">{p.title}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isApproved}
                          onClick={() =>
                            setMoveDialog({
                              projectId: p.id,
                              projectTitle: p.title,
                              sourceRoomId: room.id,
                            })
                          }
                        >
                          Переместить
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Move dialog */}
          {moveDialog && (
            <Card className="border-primary">
              <CardHeader>
                <CardTitle className="text-base">
                  Переместить: {moveDialog.projectTitle}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">Выберите целевой зал:</p>
                <div className="flex flex-wrap gap-2">
                  {clusteringResult.rooms
                    .filter((r) => r.id !== moveDialog.sourceRoomId)
                    .map((room) => (
                      <Button
                        key={room.id}
                        variant="outline"
                        size="sm"
                        disabled={moveMutation.isPending}
                        onClick={() =>
                          moveMutation.mutate({
                            runId: clusteringResult.id,
                            projectId: moveDialog.projectId,
                            targetRoomId: room.id,
                          })
                        }
                      >
                        {room.name}
                      </Button>
                    ))}
                </div>
                <Button variant="ghost" size="sm" onClick={() => setMoveDialog(null)}>
                  Отмена
                </Button>
                {moveMutation.isError && (
                  <p className="text-sm text-red-500">Ошибка перемещения</p>
                )}
              </CardContent>
            </Card>
          )}

          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={() => setCurrentStep(3)} className="w-full sm:w-auto">Далее</Button>
            <Button variant="outline" onClick={() => setCurrentStep(1)} className="w-full sm:w-auto">
              Назад
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Approve */}
      {currentStep === 3 && clusteringResult && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Итого</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm">Залов: {clusteringResult.rooms.length}</p>
              <p className="text-sm">
                Проектов:{" "}
                {clusteringResult.rooms.reduce((sum, r) => sum + r.project_count, 0)}
              </p>
              {isApproved ? (
                <div className="space-y-3">
                  <p className="text-sm text-green-600 font-medium">
                    Кластеризация одобрена
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => setCurrentStep(2)}
                    className="w-full sm:w-auto"
                  >
                    Назад к редактированию
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row gap-2 pt-2">
                  <Button
                    onClick={() => approveMutation.mutate(clusteringResult.id)}
                    disabled={approveMutation.isPending}
                    className="w-full sm:w-auto"
                  >
                    {approveMutation.isPending ? "Одобрение..." : "Одобрить"}
                  </Button>
                  <Button variant="outline" onClick={() => setCurrentStep(2)} className="w-full sm:w-auto">
                    Назад
                  </Button>
                </div>
              )}
              {approveMutation.isError && (
                <p className="text-sm text-red-500">Ошибка одобрения</p>
              )}
            </CardContent>
          </Card>
          <RoomsGrid rooms={clusteringResult.rooms} />
        </div>
      )}
    </div>
  )
}

function RoomsGrid({ rooms }: { rooms: ClusteringRoom[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      {rooms.map((room) => (
        <Card key={room.id}>
          <CardHeader>
            <CardTitle className="text-base">
              {room.name}{" "}
              <span className="text-muted-foreground font-normal">
                ({room.project_count})
              </span>
            </CardTitle>
            <p className="text-xs text-muted-foreground">{room.theme_rationale}</p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {room.projects.map((p) => (
                <li key={p.id} className="text-sm truncate">
                  {p.title}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
