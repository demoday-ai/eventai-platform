import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Stepper } from "../components/ui/stepper"
import { APP_NAME } from "../lib/constants"
import {
  generateSchedule,
  getSchedule,
  approveSchedule,
  updateSlot,
  getScheduleChanges,
  getCurrentClustering,
  type ScheduleGenerateResult,
  type ScheduleApproveResult,
  type ScheduleSlotResponse,
  type SlotUpdateRequest,
  type RoomTimeOverride,
  type BreakTime,
} from "../lib/api-client"

const STEPS = ["Генерация", "Просмотр", "Одобрение"]

export function Schedule() {
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(0)
  const [slotDuration, setSlotDuration] = useState(15)
  const [generateResult, setGenerateResult] = useState<ScheduleGenerateResult | null>(null)
  const [approveResult, setApproveResult] = useState<ScheduleApproveResult | null>(null)
  const [editingSlot, setEditingSlot] = useState<ScheduleSlotResponse | null>(null)
  const [editForm, setEditForm] = useState<SlotUpdateRequest>({})
  const [roomOverrides, setRoomOverrides] = useState<Record<string, { start_time: string; end_time: string }>>({})
  const [breaks, setBreaks] = useState<{ start_time: string; end_time: string }[]>([])

  useEffect(() => {
    document.title = `${APP_NAME} - Расписание`
  }, [])

  // Load clustering rooms for per-room time overrides
  const { data: clusteringData } = useQuery({
    queryKey: ["clustering"],
    queryFn: () => getCurrentClustering(),
    retry: false,
  })

  // Initialize roomOverrides from clustering rooms
  useEffect(() => {
    if (clusteringData?.rooms && Object.keys(roomOverrides).length === 0) {
      const initial: Record<string, { start_time: string; end_time: string }> = {}
      for (const room of clusteringData.rooms) {
        initial[room.id] = { start_time: "10:30", end_time: "19:30" }
      }
      setRoomOverrides(initial)
    }
  }, [clusteringData]) // eslint-disable-line react-hooks/exhaustive-deps

  // Try to load existing schedule
  const { data: existingSchedule } = useQuery({
    queryKey: ["schedule"],
    queryFn: () => getSchedule(),
    retry: false,
  })

  const hasAutoAdvanced = useRef(false)
  useEffect(() => {
    if (existingSchedule && existingSchedule.days.length > 0 && !hasAutoAdvanced.current) {
      hasAutoAdvanced.current = true
      setCurrentStep(1)
    }
  }, [existingSchedule])

  // Change log query
  const { data: changeLog } = useQuery({
    queryKey: ["scheduleChanges"],
    queryFn: () => getScheduleChanges(),
    enabled: currentStep === 1,
  })

  const generateMutation = useMutation({
    mutationFn: () => {
      const roomOverridesList: RoomTimeOverride[] = Object.entries(roomOverrides).map(
        ([room_id, times]) => ({ room_id, ...times })
      )
      const breaksList: BreakTime[] = breaks.filter(b => b.start_time && b.end_time)
      return generateSchedule({
        slot_duration_minutes: slotDuration,
        room_overrides: roomOverridesList.length > 0 ? roomOverridesList : undefined,
        breaks: breaksList.length > 0 ? breaksList : undefined,
        force: true,
      })
    },
    onSuccess: (data) => {
      setGenerateResult(data)
      setCurrentStep(1)
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: approveSchedule,
    onSuccess: (data) => {
      setApproveResult(data)
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
    },
  })

  const updateSlotMutation = useMutation({
    mutationFn: ({ slotId, body }: { slotId: string; body: SlotUpdateRequest }) =>
      updateSlot(slotId, body),
    onSuccess: () => {
      setEditingSlot(null)
      setEditForm({})
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["scheduleChanges"] })
    },
  })

  const scheduleData = existingSchedule

  // Collect all room options from schedule for the edit form
  const allRooms = scheduleData
    ? Array.from(
        new Map(
          scheduleData.days
            .flatMap((d) => d.rooms)
            .map((r) => [r.room_id, { id: r.room_id, name: r.room_name }])
        ).values()
      )
    : []

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString)
      return date.toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoString
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString("ru-RU", {
        weekday: "long",
        day: "numeric",
        month: "long",
      })
    } catch {
      return dateStr
    }
  }

  const startEdit = (slot: ScheduleSlotResponse) => {
    setEditingSlot(slot)
    setEditForm({
      start_time: slot.start_time,
      end_time: slot.end_time,
      room_id: slot.room_id,
      status: slot.status,
    })
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Расписание</h2>

      <Stepper steps={STEPS} currentStep={currentStep} />

      {/* Step 0: Generate */}
      {currentStep === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Генерация расписания</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="slot-duration">Длительность слота (минуты)</Label>
              <Input
                id="slot-duration"
                type="number"
                min={5}
                max={60}
                value={slotDuration}
                onChange={(e) => setSlotDuration(Number(e.target.value))}
              />
            </div>

            {/* Per-room time overrides */}
            {clusteringData?.rooms && clusteringData.rooms.length > 0 && (
              <div className="space-y-2">
                <Label>Время по залам</Label>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Зал</th>
                        <th className="py-2 pr-4">Начало</th>
                        <th className="py-2">Конец</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clusteringData.rooms.map((room) => (
                        <tr key={room.id} className="border-b">
                          <td className="py-2 pr-4">{room.name}</td>
                          <td className="py-2 pr-4">
                            <Input
                              type="time"
                              value={roomOverrides[room.id]?.start_time || "10:30"}
                              onChange={(e) =>
                                setRoomOverrides((prev) => ({
                                  ...prev,
                                  [room.id]: { ...prev[room.id], start_time: e.target.value },
                                }))
                              }
                              className="w-32"
                              aria-label={`Начало ${room.name}`}
                            />
                          </td>
                          <td className="py-2">
                            <Input
                              type="time"
                              value={roomOverrides[room.id]?.end_time || "19:30"}
                              onChange={(e) =>
                                setRoomOverrides((prev) => ({
                                  ...prev,
                                  [room.id]: { ...prev[room.id], end_time: e.target.value },
                                }))
                              }
                              className="w-32"
                              aria-label={`Конец ${room.name}`}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Breaks */}
            <div className="space-y-2">
              <Label>Перерывы</Label>
              {breaks.map((brk, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Input
                    type="time"
                    value={brk.start_time}
                    onChange={(e) => {
                      const updated = [...breaks]
                      updated[idx] = { ...updated[idx], start_time: e.target.value }
                      setBreaks(updated)
                    }}
                    className="w-32"
                    aria-label={`Начало перерыва ${idx + 1}`}
                  />
                  <span className="text-muted-foreground">—</span>
                  <Input
                    type="time"
                    value={brk.end_time}
                    onChange={(e) => {
                      const updated = [...breaks]
                      updated[idx] = { ...updated[idx], end_time: e.target.value }
                      setBreaks(updated)
                    }}
                    className="w-32"
                    aria-label={`Конец перерыва ${idx + 1}`}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setBreaks(breaks.filter((_, i) => i !== idx))}
                    aria-label={`Удалить перерыв ${idx + 1}`}
                  >
                    Удалить
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setBreaks([...breaks, { start_time: "13:00", end_time: "14:00" }])}
              >
                Добавить перерыв
              </Button>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
              >
                {generateMutation.isPending ? "Генерация..." : "Сгенерировать"}
              </Button>
              {existingSchedule && existingSchedule.days.length > 0 && (
                <Button variant="outline" onClick={() => setCurrentStep(1)}>Далее</Button>
              )}
            </div>
            {generateMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка:{" "}
                {generateMutation.error instanceof Error
                  ? generateMutation.error.message
                  : "Неизвестная ошибка"}
              </p>
            )}
            {generateResult && (
              <div className="text-sm text-muted-foreground">
                Создано {generateResult.total_slots} слотов в {generateResult.rooms.length} залах
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 1: View */}
      {currentStep === 1 && scheduleData && (
        <div className="space-y-4">
          {scheduleData.days.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-center">Расписание пусто</p>
              </CardContent>
            </Card>
          ) : (
            scheduleData.days.map((day) => (
              <div key={day.date} className="space-y-3">
                <h3 className="text-lg font-semibold capitalize">{formatDate(day.date)}</h3>
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {day.rooms.map((room) => (
                    <Card key={room.room_id}>
                      <CardHeader>
                        <CardTitle className="text-base">
                          {room.room_name}{" "}
                          <span className="text-muted-foreground font-normal">
                            ({room.slots.length})
                          </span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1">
                          {room.slots.map((slot) => (
                            <div key={slot.id}>
                              <div className="flex items-center gap-2 text-sm border rounded px-2 py-1">
                                <span className="text-muted-foreground whitespace-nowrap">
                                  {formatTime(slot.start_time)}–{formatTime(slot.end_time)}
                                </span>
                                <span className="truncate flex-1">{slot.project_title}</span>
                                {slot.project_author && (
                                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {slot.project_author}
                                  </span>
                                )}
                                <button
                                  className="text-muted-foreground hover:text-foreground ml-1 flex-shrink-0"
                                  title="Редактировать"
                                  onClick={() => startEdit(slot)}
                                  aria-label={`Редактировать ${slot.project_title}`}
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
                                </button>
                              </div>
                              {/* Inline edit form */}
                              {editingSlot?.id === slot.id && (
                                <Card className="mt-1 border-primary">
                                  <CardContent className="pt-4 space-y-3">
                                    <div className="grid gap-2 grid-cols-2">
                                      <div>
                                        <Label>Начало</Label>
                                        <Input
                                          type="datetime-local"
                                          value={editForm.start_time?.slice(0, 16) || ""}
                                          onChange={(e) =>
                                            setEditForm({ ...editForm, start_time: e.target.value })
                                          }
                                        />
                                      </div>
                                      <div>
                                        <Label>Конец</Label>
                                        <Input
                                          type="datetime-local"
                                          value={editForm.end_time?.slice(0, 16) || ""}
                                          onChange={(e) =>
                                            setEditForm({ ...editForm, end_time: e.target.value })
                                          }
                                        />
                                      </div>
                                    </div>
                                    <div>
                                      <Label>Зал</Label>
                                      <select
                                        className="w-full rounded-md border px-3 py-2 text-sm"
                                        value={editForm.room_id || ""}
                                        onChange={(e) =>
                                          setEditForm({ ...editForm, room_id: e.target.value })
                                        }
                                      >
                                        {allRooms.map((r) => (
                                          <option key={r.id} value={r.id}>{r.name}</option>
                                        ))}
                                      </select>
                                    </div>
                                    <div>
                                      <Label>Статус</Label>
                                      <select
                                        className="w-full rounded-md border px-3 py-2 text-sm"
                                        value={editForm.status || ""}
                                        onChange={(e) =>
                                          setEditForm({ ...editForm, status: e.target.value })
                                        }
                                      >
                                        <option value="scheduled">Запланирован</option>
                                        <option value="cancelled">Отменён</option>
                                      </select>
                                    </div>
                                    <div className="flex gap-2">
                                      <Button
                                        size="sm"
                                        disabled={updateSlotMutation.isPending}
                                        onClick={() =>
                                          updateSlotMutation.mutate({
                                            slotId: slot.id,
                                            body: editForm,
                                          })
                                        }
                                      >
                                        {updateSlotMutation.isPending ? "Сохранение..." : "Сохранить"}
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => {
                                          setEditingSlot(null)
                                          setEditForm({})
                                        }}
                                      >
                                        Отмена
                                      </Button>
                                    </div>
                                    {updateSlotMutation.isError && (
                                      <p className="text-xs text-red-500">Ошибка сохранения</p>
                                    )}
                                  </CardContent>
                                </Card>
                              )}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))
          )}

          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={() => setCurrentStep(2)} className="w-full sm:w-auto">Далее</Button>
            <Button variant="outline" onClick={() => setCurrentStep(0)} className="w-full sm:w-auto">
              Перегенерировать
            </Button>
          </div>

          {/* Change Log */}
          {changeLog && changeLog.items.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>История изменений</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Проект</th>
                        <th className="py-2 pr-4">Тип</th>
                        <th className="py-2 pr-4">Старое время</th>
                        <th className="py-2 pr-4">Новое время</th>
                        <th className="py-2 pr-4">Старый зал</th>
                        <th className="py-2 pr-4">Новый зал</th>
                        <th className="py-2 pr-4">Кем</th>
                        <th className="py-2 pr-4">Дата</th>
                        <th className="py-2">Уведомл.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {changeLog.items.map((ch) => (
                        <tr key={ch.id} className="border-b">
                          <td className="py-2 pr-4 font-medium">{ch.project_title}</td>
                          <td className="py-2 pr-4">{ch.change_type}</td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground">
                            {ch.old_start_time ? formatTime(ch.old_start_time) : "—"}
                          </td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground">
                            {ch.new_start_time ? formatTime(ch.new_start_time) : "—"}
                          </td>
                          <td className="py-2 pr-4 text-xs">{ch.old_room_name || "—"}</td>
                          <td className="py-2 pr-4 text-xs">{ch.new_room_name || "—"}</td>
                          <td className="py-2 pr-4 text-xs">{ch.changed_by}</td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(ch.created_at).toLocaleString("ru-RU")}
                          </td>
                          <td className="py-2">
                            {ch.notifications_sent > 0 ? (
                              <span className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                                {ch.notifications_sent}
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">0</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Step 2: Approve */}
      {currentStep === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Одобрение расписания</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {scheduleData && (
              <div className="text-sm space-y-1">
                <p>Дней: {scheduleData.days.length}</p>
                <p>
                  Залов:{" "}
                  {new Set(
                    scheduleData.days.flatMap((d) => d.rooms.map((r) => r.room_id))
                  ).size}
                </p>
                <p>
                  Слотов:{" "}
                  {scheduleData.days.reduce(
                    (sum, d) => sum + d.rooms.reduce((s, r) => s + r.slots.length, 0),
                    0
                  )}
                </p>
              </div>
            )}

            {approveResult ? (
              <p className="text-sm text-green-600 font-medium">
                Расписание одобрено: {approveResult.total_slots} слотов, {approveResult.rooms} залов, {approveResult.days} дней
              </p>
            ) : (
              <div className="flex flex-col sm:flex-row gap-2">
                <Button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                  className="w-full sm:w-auto"
                >
                  {approveMutation.isPending ? "Одобрение..." : "Одобрить"}
                </Button>
                <Button variant="outline" onClick={() => setCurrentStep(1)} className="w-full sm:w-auto">
                  Назад
                </Button>
              </div>
            )}
            {approveMutation.isError && (
              <p className="text-sm text-red-500">Ошибка одобрения</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
