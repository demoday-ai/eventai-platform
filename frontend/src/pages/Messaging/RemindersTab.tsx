import React, { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import { StatusBadge } from "../../components/shared/StatusBadge"
import { useAuth } from "../../hooks/useAuth"
import {
  getScheduleReminderPreview,
  sendReminders,
  cancelReminders,
  getReminderBatches,
  getReminderBatchDetail,
  type ScheduleReminderPreview,
  type ReminderSendResult,
  type ReminderCancelResult,
  type ReminderBatchDetail,
} from "../../lib/api-client"

export function RemindersTab() {
  const { telegramId } = useAuth()
  const [reminderDay, setReminderDay] = useState("")
  const [reminderPreview, setReminderPreview] = useState<ScheduleReminderPreview | null>(null)
  const [reminderSendResult, setReminderSendResult] = useState<ReminderSendResult | null>(null)
  const [reminderCancelResult, setReminderCancelResult] = useState<ReminderCancelResult | null>(null)
  const [expandedBatchId, setExpandedBatchId] = useState<string | null>(null)
  const [batchDetail, setBatchDetail] = useState<ReminderBatchDetail | null>(null)

  const { data: batchHistory, isLoading: batchLoading } = useQuery({
    queryKey: ["reminderBatches", telegramId],
    queryFn: () => getReminderBatches(telegramId!),
    enabled: !!telegramId,
  })

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

  const loadBatchDetail = async (batchId: string) => {
    if (expandedBatchId === batchId) {
      setExpandedBatchId(null)
      setBatchDetail(null)
      return
    }
    setExpandedBatchId(batchId)
    const detail = await getReminderBatchDetail(batchId, telegramId!)
    setBatchDetail(detail)
  }

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

      <Card>
        <CardHeader><CardTitle>История рассылок</CardTitle></CardHeader>
        <CardContent>
          {batchLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {batchHistory && batchHistory.batches.length === 0 && (
            <p className="text-muted-foreground text-sm">Нет рассылок</p>
          )}
          {batchHistory && batchHistory.batches.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-4">Тип</th>
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Инициатор</th>
                    <th className="py-2 pr-4">Всего</th>
                    <th className="py-2 pr-4">Отправлено</th>
                    <th className="py-2 pr-4">Ошибок</th>
                    <th className="py-2 pr-4">Пропущено</th>
                    <th className="py-2">Начато</th>
                  </tr>
                </thead>
                <tbody>
                  {batchHistory.batches.map((batch) => (
                    <React.Fragment key={batch.id}>
                      <tr
                        className="border-b cursor-pointer hover:bg-muted/50"
                        onClick={() => loadBatchDetail(batch.id)}
                      >
                        <td className="py-2 pr-4">{batch.reminder_type}</td>
                        <td className="py-2 pr-4"><StatusBadge status={batch.status} variant="notification" /></td>
                        <td className="py-2 pr-4">{batch.initiated_by_name}</td>
                        <td className="py-2 pr-4">{batch.total_recipients}</td>
                        <td className="py-2 pr-4">{batch.sent}</td>
                        <td className="py-2 pr-4">{batch.failed}</td>
                        <td className="py-2 pr-4">{batch.skipped}</td>
                        <td className="py-2 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(batch.started_at).toLocaleString("ru-RU")}
                        </td>
                      </tr>
                      {expandedBatchId === batch.id && batchDetail && (
                        <tr>
                          <td colSpan={8} className="py-2 px-4 bg-muted/30">
                            <p className="text-sm font-medium mb-1">По типам получателей:</p>
                            {Object.entries(batchDetail.by_recipient_type).map(([role, stats]) => (
                              <p key={role} className="text-xs text-muted-foreground">
                                {role}: отправлено {stats.sent}, ошибок {stats.failed}, пропущено {stats.skipped}
                              </p>
                            ))}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
