import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Stepper } from "../components/ui/stepper"
import { APP_NAME } from "../lib/constants"
import {
  runClustering,
  getCurrentClustering,
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
  const [moveDialog, setMoveDialog] = useState<{
    projectId: string
    projectTitle: string
    sourceRoomId: string
  } | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Кластеризация`
  }, [])

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

  const runMutation = useMutation({
    mutationFn: () =>
      runClustering({
        num_rooms: numRooms,
        feedback: feedback || null,
      }),
    onSuccess: (data) => {
      setClusteringResult(data)
      setFeedback("")
      setCurrentStep(1)
      queryClient.invalidateQueries({ queryKey: ["clustering"] })
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
                onChange={(e) => setNumRooms(Number(e.target.value))}
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
              />
            </div>
            <Button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
            >
              {runMutation.isPending ? "Кластеризация..." : "Запустить"}
            </Button>
            {runMutation.isError && (
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
          <div className="flex gap-2">
            <Button onClick={() => setCurrentStep(2)}>Далее</Button>
            <Button
              variant="outline"
              onClick={() => {
                setCurrentStep(0)
              }}
            >
              Перезапустить
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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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

          <div className="flex gap-2">
            <Button onClick={() => setCurrentStep(3)}>Далее</Button>
            <Button variant="outline" onClick={() => setCurrentStep(1)}>
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
                <p className="text-sm text-green-600 font-medium">
                  Кластеризация одобрена
                </p>
              ) : (
                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={() => approveMutation.mutate(clusteringResult.id)}
                    disabled={approveMutation.isPending}
                  >
                    {approveMutation.isPending ? "Одобрение..." : "Одобрить"}
                  </Button>
                  <Button variant="outline" onClick={() => setCurrentStep(2)}>
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
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
