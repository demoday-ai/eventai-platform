import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Users } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Stepper } from "../components/ui/stepper"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import {
  runMatching,
  getCurrentMatching,
  getCurrentClustering,
  moveExpert,
  assignExpert,
  approveMatching,
  getInvitePreview,
  confirmInvites,
  type MatchingResult,
  type InvitePreview,
  type InviteConfirmResult,
} from "../lib/api-client"

const STEPS = ["Матчинг", "Результат и корректировка", "Одобрение и приглашения"]

function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail && typeof detail === "object" && "message" in detail) return (detail as { message: string }).message
  }
  if (error instanceof Error) return error.message
  return "Неизвестная ошибка"
}

function detectStep(matching: MatchingResult | null | undefined): number {
  if (!matching) return 0
  // No assigned experts → stay on step 1 to show results (user can manually assign)
  if (matching.matched_experts === 0) return 1
  // Some are approved/invite_ready → step 2
  const hasApproved = matching.rooms.some((r) =>
    r.experts.some((e) => "status" in e && ((e as Record<string, unknown>).status === "approved" || (e as Record<string, unknown>).status === "invite_ready"))
  )
  if (hasApproved) return 2
  return 1
}

interface ExpertMatchingTabProps {
  onSwitchTab: (tab: string) => void
}

export function ExpertMatchingTab({ onSwitchTab }: ExpertMatchingTabProps) {
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(0)
  const [useAdjacentTags, setUseAdjacentTags] = useState(true)
  const [matchingError, setMatchingError] = useState<string | null>(null)
  const [movingExpertId, setMovingExpertId] = useState<string | null>(null)
  const [assigningExpertId, setAssigningExpertId] = useState<string | null>(null)
  const [invitePreview, setInvitePreview] = useState<InvitePreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [inviteResult, setInviteResult] = useState<InviteConfirmResult | null>(null)
  const [stepDetected, setStepDetected] = useState(false)
  const [showApproveConfirm, setShowApproveConfirm] = useState(false)

  // Check if approved clustering exists
  const { data: clusteringData, isFetched: clusteringFetched } = useQuery({
    queryKey: ["clustering"],
    queryFn: getCurrentClustering,
    retry: false,
  })

  // Load existing matching
  const { data: existingMatching } = useQuery({
    queryKey: ["matching"],
    queryFn: getCurrentMatching,
    retry: false,
  })

  const [matchingResult, setMatchingResult] = useState<MatchingResult | null>(null)

  // Auto-detect current step based on existing data
  useEffect(() => {
    if (existingMatching && !stepDetected) {
      setMatchingResult(existingMatching)
      setCurrentStep(detectStep(existingMatching))
      setStepDetected(true)
    }
  }, [existingMatching, stepDetected])

  const runMutation = useMutation({
    mutationFn: () => runMatching({ use_adjacent_tags: useAdjacentTags }),
    onSuccess: (data) => {
      setMatchingResult(data)
      setMatchingError(null)
      setCurrentStep(1)
      setStepDetected(true)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
    onError: (error) => {
      setMatchingError(getErrorMessage(error))
    },
  })

  const moveMutation = useMutation({
    mutationFn: ({ assignmentId, targetRoomId }: { assignmentId: string; targetRoomId: string }) =>
      moveExpert(assignmentId, targetRoomId),
    onSuccess: () => {
      setMovingExpertId(null)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
  })

  const assignMutation = useMutation({
    mutationFn: ({ expertId, roomId }: { expertId: string; roomId: string }) =>
      assignExpert(expertId, roomId),
    onSuccess: () => {
      setAssigningExpertId(null)
      queryClient.invalidateQueries({ queryKey: ["matching"] })
    },
  })

  // Refetch matching after move or assign
  const { data: refreshedMatching } = useQuery({
    queryKey: ["matching"],
    queryFn: getCurrentMatching,
    enabled: moveMutation.isSuccess || assignMutation.isSuccess,
  })

  useEffect(() => {
    if (refreshedMatching && (moveMutation.isSuccess || assignMutation.isSuccess)) {
      setMatchingResult(refreshedMatching)
    }
  }, [refreshedMatching, moveMutation.isSuccess, assignMutation.isSuccess])

  const approveMutation = useMutation({
    mutationFn: approveMatching,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matching"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      setShowApproveConfirm(false)
      previewMutation.mutate()
    },
  })

  const previewMutation = useMutation({
    mutationFn: getInvitePreview,
    onSuccess: (data) => {
      setInvitePreview(data)
      setPreviewError(null)
    },
    onError: (error) => {
      const detail = getErrorMessage(error)
      if (error instanceof AxiosError && error.response?.status === 404) {
        setPreviewError(detail || "Нет данных для предпросмотра. Запустите матчинг.")
      } else {
        setPreviewError(detail || "Ошибка сервера. Попробуйте обновить страницу.")
      }
    },
  })

  const confirmMutation = useMutation({
    mutationFn: confirmInvites,
    onSuccess: (data) => {
      setInviteResult(data)
    },
  })

  // Auto-load invite preview when entering step 2 (only if there are matched experts)
  useEffect(() => {
    if (currentStep === 2 && !invitePreview && !previewMutation.isPending && !previewError && matchingResult && matchingResult.matched_experts > 0) {
      previewMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep])

  const allRooms = matchingResult?.rooms || []
  const hasMatched = matchingResult ? matchingResult.matched_experts > 0 : false

  const hasNoApprovedClustering = clusteringFetched && !clusteringData?.approved_at && !existingMatching

  if (hasNoApprovedClustering) {
    return (
      <PageEmptyState
        icon={Users}
        title="Для матчинга экспертов необходима одобренная кластеризация"
        description="Одобрите кластеризацию, чтобы начать матчинг."
        actionLabel="Перейти к кластеризации"
        actionLink="/clustering"
      />
    )
  }

  return (
    <div className="grid gap-6">
      <Stepper steps={STEPS} currentStep={currentStep} />

      {/* Step 0: Run matching */}
      {currentStep === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Запуск матчинга</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Автоматическое распределение экспертов по залам на основе тегов.
              Требуется одобренная кластеризация.
            </p>
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
              onClick={() => {
                setMatchingError(null)
                runMutation.mutate()
              }}
              disabled={runMutation.isPending}
            >
              {runMutation.isPending ? "Матчинг выполняется..." : "Запустить матчинг"}
            </Button>

            {runMutation.isPending && (
              <div className="p-3 bg-blue-50 rounded-md">
                <p className="text-sm text-blue-800">
                  Матчинг выполняется... Это может занять до минуты.
                </p>
              </div>
            )}

            {matchingResult && (
              <Button variant="outline" onClick={() => setCurrentStep(1)}>Далее</Button>
            )}

            {matchingError && (
              <p className="text-sm text-red-500">
                Ошибка: {matchingError}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 1: Results + Move + Assign (merged) */}
      {currentStep === 1 && matchingResult && (
        <div className="space-y-4">
          {/* Stats */}
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

          {/* Warning when 0 matched */}
          {!hasMatched && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md space-y-2">
              <p className="text-sm font-medium text-yellow-800">
                Автоматический матчинг не смог назначить экспертов — теги не совпали с тематиками залов.
              </p>
              <p className="text-sm text-yellow-700">
                Назначьте экспертов вручную из списка ниже, или{" "}
                <button onClick={() => onSwitchTab("list")} className="underline font-medium">
                  проверьте теги экспертов
                </button>{" "}
                и перезапустите матчинг.
              </p>
            </div>
          )}

          {/* Unmatched experts — inline assign */}
          {matchingResult.unmatched && matchingResult.unmatched.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Не назначены ({matchingResult.unmatched.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {matchingResult.unmatched.map((exp) => {
                    const isExpanded = assigningExpertId === exp.expert_id
                    return (
                      <div key={exp.expert_id} className="text-sm border rounded px-3 py-2">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0 mr-2">
                            <span className="font-medium">{exp.name}</span>
                            {exp.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {exp.tags.map((tag) => (
                                  <span key={tag} className="px-1.5 py-0.5 bg-muted text-xs rounded">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                            {exp.tags.length === 0 && (
                              <span className="text-xs text-muted-foreground ml-2">нет тегов</span>
                            )}
                          </div>
                          <Button
                            variant={isExpanded ? "secondary" : "outline"}
                            size="sm"
                            onClick={() => setAssigningExpertId(isExpanded ? null : exp.expert_id)}
                          >
                            {isExpanded ? "Отмена" : "Назначить"}
                          </Button>
                        </div>
                        {isExpanded && (
                          <div className="mt-2 pt-2 border-t flex flex-wrap gap-2">
                            {allRooms.map((room) => (
                              <Button
                                key={room.room_id}
                                variant="outline"
                                size="sm"
                                disabled={assignMutation.isPending}
                                onClick={() =>
                                  assignMutation.mutate({
                                    expertId: exp.expert_id,
                                    roomId: room.room_id,
                                  })
                                }
                              >
                                {room.room_name} ({room.expert_count})
                              </Button>
                            ))}
                            {assignMutation.isError && assignMutation.variables?.expertId === exp.expert_id && (
                              <p className="text-sm text-red-500 w-full">
                                {getErrorMessage(assignMutation.error)}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Room cards — inline move */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {allRooms.map((room) => (
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
                  {room.experts.length === 0 && (
                    <p className="text-sm text-muted-foreground">Нет экспертов</p>
                  )}
                  <ul className="space-y-2">
                    {room.experts.map((exp) => {
                      const isMoving = movingExpertId === exp.expert_id
                      return (
                        <li key={exp.expert_id} className="text-sm border rounded px-2 py-1">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{exp.name}</span>
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-muted-foreground">
                                {exp.is_manual ? "вручную" : `${(exp.match_score * 100).toFixed(0)}%`}
                              </span>
                              <Button
                                variant={isMoving ? "secondary" : "ghost"}
                                size="sm"
                                className="h-6 px-2 text-xs"
                                onClick={() => setMovingExpertId(isMoving ? null : exp.expert_id)}
                              >
                                {isMoving ? "Отмена" : "Переместить"}
                              </Button>
                            </div>
                          </div>
                          {!isMoving && exp.matching_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {exp.matching_tags.map((tag) => (
                                <span key={tag} className="px-1.5 py-0.5 bg-muted text-xs rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {isMoving && (
                            <div className="mt-2 pt-2 border-t flex flex-wrap gap-1">
                              {allRooms
                                .filter((r) => r.room_id !== room.room_id)
                                .map((r) => (
                                  <Button
                                    key={r.room_id}
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs"
                                    disabled={moveMutation.isPending}
                                    onClick={() =>
                                      moveMutation.mutate({
                                        assignmentId: exp.expert_id,
                                        targetRoomId: r.room_id,
                                      })
                                    }
                                  >
                                    {r.room_name}
                                  </Button>
                                ))}
                              {moveMutation.isError && moveMutation.variables?.assignmentId === exp.expert_id && (
                                <p className="text-sm text-red-500 w-full">{getErrorMessage(moveMutation.error)}</p>
                              )}
                            </div>
                          )}
                        </li>
                      )
                    })}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Navigation */}
          <div className="flex flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={() => setCurrentStep(0)} className="w-full sm:w-auto">
              Перезапустить матчинг
            </Button>
            <Button
              onClick={() => setCurrentStep(2)}
              disabled={!hasMatched}
              className="w-full sm:w-auto"
            >
              Далее
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Approve + Invites (merged) */}
      {currentStep === 2 && (
        <div className="space-y-4">
          {matchingResult && (
            <Card>
              <CardHeader>
                <CardTitle>Одобрение и приглашения</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm">
                  Всего экспертов: {matchingResult.total_experts}, назначены: {matchingResult.matched_experts}
                </p>

                {!approveMutation.isSuccess && !showApproveConfirm && (
                  <Button
                    onClick={() => setShowApproveConfirm(true)}
                    disabled={approveMutation.isPending || !hasMatched}
                    className="w-full sm:w-auto"
                  >
                    Одобрить матчинг
                  </Button>
                )}

                {showApproveConfirm && !approveMutation.isSuccess && (
                  <div className="p-4 border rounded-md space-y-3">
                    <p className="text-sm font-medium">Вы уверены, что хотите одобрить матчинг?</p>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => approveMutation.mutate()}
                        disabled={approveMutation.isPending}
                      >
                        {approveMutation.isPending ? "Одобрение..." : "Подтвердить"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setShowApproveConfirm(false)}
                        disabled={approveMutation.isPending}
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                )}

                {approveMutation.isSuccess && (
                  <div className="space-y-3">
                    <p className="text-sm text-green-600 font-medium">Матчинг одобрён</p>
                    <Card className="border-green-200">
                      <CardContent className="pt-4">
                        <p className="text-sm">Следующий шаг — генерация расписания</p>
                        <Link to="/schedule">
                          <Button variant="outline" size="sm" className="mt-2">
                            Перейти к расписанию
                          </Button>
                        </Link>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {approveMutation.isError && (
                  <p className="text-sm text-red-500">Ошибка одобрения: {getErrorMessage(approveMutation.error)}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Invite preview — auto-loads */}
          {previewMutation.isPending && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">Загрузка предпросмотра приглашений...</p>
              </CardContent>
            </Card>
          )}

          {previewError && !invitePreview && (
            <Card>
              <CardContent className="pt-4 space-y-2">
                <p className="text-sm text-red-500">{previewError}</p>
                <Button variant="outline" size="sm" onClick={() => {
                  setPreviewError(null)
                  previewMutation.mutate()
                }}>
                  Повторить
                </Button>
              </CardContent>
            </Card>
          )}

          {invitePreview && !inviteResult && (
            <Card>
              <CardHeader>
                <CardTitle>Предпросмотр приглашений</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {invitePreview.has_unapproved && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-sm text-yellow-800">
                      Матчинг ещё не одобрён. Одобрите матчинг перед отправкой приглашений.
                    </p>
                  </div>
                )}

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
                  disabled={confirmMutation.isPending || invitePreview.has_unapproved}
                >
                  {confirmMutation.isPending ? "Отправка..." : "Отправить приглашения"}
                </Button>
                {confirmMutation.isError && (
                  <p className="text-sm text-red-500 mt-2">Ошибка отправки: {getErrorMessage(confirmMutation.error)}</p>
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

          <Button variant="outline" onClick={() => setCurrentStep(1)} className="w-full sm:w-auto">
            Назад
          </Button>
        </div>
      )}
    </div>
  )
}
