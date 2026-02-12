import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import {
  getScheduleReminderPreview,
  sendReminders,
  cancelReminders,
  type ScheduleReminderPreview,
  type ReminderSendResult,
  type ReminderCancelResult,
} from "../../lib/api-client"

export function RemindersTab() {
  const [reminderDay, setReminderDay] = useState("")
  const [reminderPreview, setReminderPreview] = useState<ScheduleReminderPreview | null>(null)
  const [reminderSendResult, setReminderSendResult] = useState<ReminderSendResult | null>(null)
  const [reminderCancelResult, setReminderCancelResult] = useState<ReminderCancelResult | null>(null)

  const previewMutation = useMutation({
    mutationFn: (day: string) => getScheduleReminderPreview(day || undefined),
    onSuccess: (data) => {
      setReminderPreview(data)
      setReminderSendResult(null)
      setReminderCancelResult(null)
    },
  })

  const sendMutation = useMutation({
    mutationFn: (day: string) => sendReminders(day),
    onSuccess: (data) => setReminderSendResult(data),
  })

  const cancelMutation = useMutation({
    mutationFn: (day: string) => cancelReminders(day),
    onSuccess: (data) => setReminderCancelResult(data),
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Напоминания по расписанию</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 items-end">
            <div>
              <label className="text-sm font-medium">День</label>
              <Input
                type="date"
                className="mt-1"
                value={reminderDay}
                onChange={(e) => setReminderDay(e.target.value)}
              />
            </div>
            <Button
              variant="outline"
              disabled={previewMutation.isPending}
              onClick={() => previewMutation.mutate(reminderDay)}
            >
              {previewMutation.isPending ? "Загрузка..." : "Предпросмотр"}
            </Button>
          </div>

          {previewMutation.isError && (
            <p className="text-sm text-red-500">Ошибка предпросмотра</p>
          )}

          {reminderPreview && (
            <div className="space-y-3 border rounded p-4">
              <p className="text-sm">
                День: <span className="font-medium">{reminderPreview.day}</span>
                <span className="text-muted-foreground ml-2">
                  Время отправки: {reminderPreview.scheduled_send_time}
                </span>
              </p>
              <div className="text-sm space-y-1">
                <p>Студентов: {reminderPreview.recipients.students}</p>
                <p>Экспертов: {reminderPreview.recipients.experts}</p>
                <p>Гостей: {reminderPreview.recipients.guests}</p>
                <p>Бизнес: {reminderPreview.recipients.business}</p>
                <p className="font-medium">Итого: {reminderPreview.recipients.total}</p>
              </div>

              {reminderPreview.sample_messages.student && (
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground">Примеры сообщений</summary>
                  <div className="mt-1 space-y-1 text-xs bg-muted p-2 rounded">
                    {reminderPreview.sample_messages.student && <p><b>Студент:</b> {reminderPreview.sample_messages.student}</p>}
                    {reminderPreview.sample_messages.expert && <p><b>Эксперт:</b> {reminderPreview.sample_messages.expert}</p>}
                    {reminderPreview.sample_messages.guest && <p><b>Гость:</b> {reminderPreview.sample_messages.guest}</p>}
                    {reminderPreview.sample_messages.business && <p><b>Бизнес:</b> {reminderPreview.sample_messages.business}</p>}
                  </div>
                </details>
              )}

              {reminderPreview.unreachable.length > 0 && (
                <p className="text-xs text-red-500">
                  Недоступных: {reminderPreview.unreachable.length}
                </p>
              )}

              <div className="flex gap-2">
                <Button
                  disabled={sendMutation.isPending}
                  onClick={() => sendMutation.mutate(reminderPreview.day)}
                >
                  {sendMutation.isPending ? "Отправка..." : "Отправить"}
                </Button>
                {reminderPreview.can_cancel && (
                  <Button
                    variant="outline"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(reminderPreview.day)}
                  >
                    {cancelMutation.isPending ? "Отмена..." : "Отменить"}
                  </Button>
                )}
              </div>

              {reminderSendResult && (
                <p className="text-sm text-green-600">
                  Отправлено: {reminderSendResult.sent}, ошибок: {reminderSendResult.failed}, пропущено: {reminderSendResult.skipped}
                </p>
              )}
              {reminderCancelResult && (
                <p className="text-sm text-yellow-600">
                  Отменено: {reminderCancelResult.cancelled_count}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
