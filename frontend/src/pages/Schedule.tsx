import { useState, useEffect } from "react"
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
  type ScheduleGenerateResult,
  type ScheduleApproveResult,
} from "../lib/api-client"

const STEPS = ["Генерация", "Просмотр", "Одобрение"]

export function Schedule() {
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(0)
  const [slotDuration, setSlotDuration] = useState(15)
  const [generateResult, setGenerateResult] = useState<ScheduleGenerateResult | null>(null)
  const [approveResult, setApproveResult] = useState<ScheduleApproveResult | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Расписание`
  }, [])

  // Try to load existing schedule
  const { data: existingSchedule } = useQuery({
    queryKey: ["schedule"],
    queryFn: () => getSchedule(),
    retry: false,
  })

  useEffect(() => {
    if (existingSchedule && existingSchedule.days.length > 0 && currentStep === 0) {
      setCurrentStep(1)
    }
  }, [existingSchedule, currentStep])

  const generateMutation = useMutation({
    mutationFn: () =>
      generateSchedule({ slot_duration_minutes: slotDuration }),
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

  const scheduleData = existingSchedule

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
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? "Генерация..." : "Сгенерировать"}
            </Button>
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
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
                            <div
                              key={slot.id}
                              className="flex items-center gap-2 text-sm border rounded px-2 py-1"
                            >
                              <span className="text-muted-foreground whitespace-nowrap">
                                {formatTime(slot.start_time)}–{formatTime(slot.end_time)}
                              </span>
                              <span className="truncate flex-1">{slot.project_title}</span>
                              {slot.project_author && (
                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                  {slot.project_author}
                                </span>
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

          <div className="flex gap-2">
            <Button onClick={() => setCurrentStep(2)}>Далее</Button>
            <Button variant="outline" onClick={() => setCurrentStep(0)}>
              Перегенерировать
            </Button>
          </div>
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
              <div className="flex gap-2">
                <Button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                >
                  {approveMutation.isPending ? "Одобрение..." : "Одобрить"}
                </Button>
                <Button variant="outline" onClick={() => setCurrentStep(1)}>
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
