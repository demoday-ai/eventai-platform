import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Stepper } from "../components/ui/stepper"
import { APP_NAME } from "../lib/constants"
import {
  runMatching,
  getCurrentMatching,
  moveExpert,
  approveMatching,
  getInvitePreview,
  confirmInvites,
  type MatchingResult,
  type InvitePreview,
  type InviteConfirmResult,
} from "../lib/api-client"

const STEPS = ["Запуск", "Результат", "Перемещение", "Одобрение", "Приглашения"]

export function ExpertMatching() {
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(0)
  const [useAdjacentTags, setUseAdjacentTags] = useState(true)
  const [moveDialog, setMoveDialog] = useState<{
    assignmentId: string
    expertName: string
    sourceRoomId: string
  } | null>(null)
  const [invitePreview, setInvitePreview] = useState<InvitePreview | null>(null)
  const [inviteResult, setInviteResult] = useState<InviteConfirmResult | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Эксперты`
  }, [])

  // Load existing matching
  const { data: existingMatching } = useQuery({
    queryKey: ["matching"],
    queryFn: getCurrentMatching,
    retry: false,
  })

  const [matchingResult, setMatchingResult] = useState<MatchingResult | null>(null)

  useEffect(() => {
    if (existingMatching && !matchingResult) {
      setMatchingResult(existingMatching)
      setCurrentStep(1)
    }
  }, [existingMatching, matchingResult])

  const runMutation = useMutation({
    mutationFn: () => runMatching({ use_adjacent_tags: useAdjacentTags }),
    onSuccess: (data) => {
      setMatchingResult(data)
      setCurrentStep(1)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
  })

  const moveMutation = useMutation({
    mutationFn: ({ assignmentId, targetRoomId }: { assignmentId: string; targetRoomId: string }) =>
      moveExpert(assignmentId, targetRoomId),
    onSuccess: () => {
      setMoveDialog(null)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
  })

  // Refetch matching after move
  const { data: refreshedMatching } = useQuery({
    queryKey: ["matching"],
    queryFn: getCurrentMatching,
    enabled: moveMutation.isSuccess,
  })

  useEffect(() => {
    if (refreshedMatching && moveMutation.isSuccess) {
      setMatchingResult(refreshedMatching)
    }
  }, [refreshedMatching, moveMutation.isSuccess])

  const approveMutation = useMutation({
    mutationFn: approveMatching,
    onSuccess: () => {
      setCurrentStep(4)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
  })

  const previewMutation = useMutation({
    mutationFn: getInvitePreview,
    onSuccess: (data) => {
      setInvitePreview(data)
    },
  })

  const confirmMutation = useMutation({
    mutationFn: confirmInvites,
    onSuccess: (data) => {
      setInviteResult(data)
    },
  })

  // Rooms for move target selection
  const allRooms = matchingResult?.rooms || []

  return (
    <div className="grid gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
        <h2 className="text-2xl font-bold">Эксперты</h2>
        <Link to="/experts/list">
          <Button variant="outline" size="sm" className="w-full sm:w-auto">Список экспертов</Button>
        </Link>
      </div>

      <Stepper steps={STEPS} currentStep={currentStep} />

      {/* Step 0: Run */}
      {currentStep === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Запуск матчинга</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useAdjacentTags}
                onChange={(e) => setUseAdjacentTags(e.target.checked)}
                className="rounded"
              />
              Использовать смежные теги
            </label>
            <Button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
            >
              {runMutation.isPending ? "Матчинг..." : "Запустить матчинг"}
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
      {currentStep === 1 && matchingResult && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Всего экспертов</p>
                  <p className="text-2xl font-bold">{matchingResult.total_experts}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Назначены</p>
                  <p className="text-2xl font-bold text-green-600">{matchingResult.matched_experts}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Не назначены</p>
                  <p className="text-2xl font-bold text-red-600">{matchingResult.unmatched_experts}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {matchingResult.rooms.map((room) => (
              <Card key={room.room_id}>
                <CardHeader>
                  <CardTitle className="text-base">
                    {room.room_name}{" "}
                    <span className="text-muted-foreground font-normal">
                      ({room.expert_count})
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {room.experts.map((exp) => (
                      <li key={exp.expert_id} className="text-sm border rounded px-2 py-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{exp.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {(exp.match_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {exp.matching_tags.map((tag) => (
                            <span key={tag} className="px-1.5 py-0.5 bg-muted text-xs rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={() => setCurrentStep(2)} className="w-full sm:w-auto">Далее</Button>
            <Button variant="outline" onClick={() => setCurrentStep(0)} className="w-full sm:w-auto">
              Перезапустить
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Move experts */}
      {currentStep === 2 && matchingResult && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Нажмите &quot;Переместить&quot; рядом с экспертом, чтобы перенести его в другой зал.
          </p>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {matchingResult.rooms.map((room) => (
              <Card key={room.room_id}>
                <CardHeader>
                  <CardTitle className="text-base">{room.room_name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {room.experts.map((exp) => (
                      <div key={exp.expert_id} className="flex items-center justify-between text-sm border rounded px-2 py-1">
                        <span className="truncate flex-1 mr-2">{exp.name}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setMoveDialog({
                              assignmentId: exp.expert_id,
                              expertName: exp.name,
                              sourceRoomId: room.room_id,
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

          {moveDialog && (
            <Card className="border-primary">
              <CardHeader>
                <CardTitle className="text-base">
                  Переместить: {moveDialog.expertName}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">Выберите целевой зал:</p>
                <div className="flex flex-wrap gap-2">
                  {allRooms
                    .filter((r) => r.room_id !== moveDialog.sourceRoomId)
                    .map((room) => (
                      <Button
                        key={room.room_id}
                        variant="outline"
                        size="sm"
                        disabled={moveMutation.isPending}
                        onClick={() =>
                          moveMutation.mutate({
                            assignmentId: moveDialog.assignmentId,
                            targetRoomId: room.room_id,
                          })
                        }
                      >
                        {room.room_name}
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
      {currentStep === 3 && matchingResult && (
        <Card>
          <CardHeader>
            <CardTitle>Одобрение матчинга</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm">
              Всего экспертов: {matchingResult.total_experts}, назначены: {matchingResult.matched_experts}
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <Button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="w-full sm:w-auto"
              >
                {approveMutation.isPending ? "Одобрение..." : "Одобрить"}
              </Button>
              <Button variant="outline" onClick={() => setCurrentStep(2)} className="w-full sm:w-auto">
                Назад
              </Button>
            </div>
            {approveMutation.isError && (
              <p className="text-sm text-red-500">Ошибка одобрения</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 4: Invites */}
      {currentStep === 4 && (
        <div className="space-y-4">
          {!invitePreview && !inviteResult && (
            <Card>
              <CardHeader>
                <CardTitle>Приглашения экспертам</CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={() => previewMutation.mutate()}
                  disabled={previewMutation.isPending}
                >
                  {previewMutation.isPending ? "Загрузка..." : "Предпросмотр приглашений"}
                </Button>
                {previewMutation.isError && (
                  <p className="text-sm text-red-500 mt-2">Ошибка загрузки превью</p>
                )}
              </CardContent>
            </Card>
          )}

          {invitePreview && !inviteResult && (
            <Card>
              <CardHeader>
                <CardTitle>Предпросмотр приглашений</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Всего экспертов</p>
                    <p className="text-2xl font-bold">{invitePreview.total_experts}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">С Telegram</p>
                    <p className="text-2xl font-bold text-green-600">{invitePreview.with_telegram}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Без Telegram</p>
                    <p className="text-2xl font-bold text-yellow-600">{invitePreview.without_telegram}</p>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-1">Пример сообщения:</p>
                  <pre className="text-xs bg-muted p-3 rounded whitespace-pre-wrap">
                    {invitePreview.sample_message}
                  </pre>
                </div>
                <p className="text-xs text-muted-foreground">
                  Бот: {invitePreview.bot_link}
                </p>
                <Button
                  onClick={() => confirmMutation.mutate()}
                  disabled={confirmMutation.isPending}
                >
                  {confirmMutation.isPending ? "Отправка..." : "Отправить приглашения"}
                </Button>
                {confirmMutation.isError && (
                  <p className="text-sm text-red-500 mt-2">Ошибка отправки</p>
                )}
              </CardContent>
            </Card>
          )}

          {inviteResult && (
            <Card className="border-green-300">
              <CardHeader>
                <CardTitle>Приглашения отправлены</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{inviteResult.message}</p>
                <p className="text-sm">
                  Готово к отправке: {inviteResult.invite_ready_count}
                </p>
                <p className="text-xs text-muted-foreground">
                  Бот: {inviteResult.bot_link}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
