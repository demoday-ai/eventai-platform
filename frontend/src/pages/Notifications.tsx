import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { APP_NAME } from "../lib/constants"
import { useAuth } from "../hooks/useAuth"
import {
  getNotificationDashboard,
  getNotifications,
  getScheduleReminderPreview,
  sendReminders,
  cancelReminders,
  getReminderBatches,
  getReminderBatchDetail,
  type ScheduleReminderPreview,
  type ReminderSendResult,
  type ReminderCancelResult,
  type ReminderBatchDetail,
} from "../lib/api-client"

const TABS = ["Дашборд", "Уведомления", "Рассылки"] as const
type Tab = (typeof TABS)[number]

function statusBadge(status: string) {
  switch (status) {
    case "sent":
      return <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">Отправлено</span>
    case "failed":
      return <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">Ошибка</span>
    case "pending":
      return <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">Ожидает</span>
    default:
      return <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-800">{status}</span>
  }
}

export function Notifications() {
  const { telegramId } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>("Дашборд")

  // Dashboard state
  const [dashType, setDashType] = useState("")
  const [dashDay, setDashDay] = useState("")

  // Notification list state
  const [notifType, setNotifType] = useState("")
  const [notifStatus, setNotifStatus] = useState("")
  const [notifOffset, setNotifOffset] = useState(0)
  const notifLimit = 20

  // Reminder state
  const [reminderDay, setReminderDay] = useState("")
  const [reminderPreview, setReminderPreview] = useState<ScheduleReminderPreview | null>(null)
  const [reminderSendResult, setReminderSendResult] = useState<ReminderSendResult | null>(null)
  const [reminderCancelResult, setReminderCancelResult] = useState<ReminderCancelResult | null>(null)
  const [expandedBatchId, setExpandedBatchId] = useState<string | null>(null)
  const [batchDetail, setBatchDetail] = useState<ReminderBatchDetail | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Уведомления`
  }, [])

  // Dashboard query
  const { data: dashboard, isLoading: dashLoading, isError: dashError } = useQuery({
    queryKey: ["notificationDashboard", dashType, dashDay],
    queryFn: () =>
      getNotificationDashboard({
        type: dashType || undefined,
        day: dashDay || undefined,
      }),
    enabled: activeTab === "Дашборд",
  })

  // Notifications list query
  const { data: notifList, isLoading: notifLoading } = useQuery({
    queryKey: ["notifications", notifType, notifStatus, notifOffset],
    queryFn: () =>
      getNotifications({
        type: notifType || undefined,
        status: notifStatus || undefined,
        offset: notifOffset,
        limit: notifLimit,
      }),
    enabled: activeTab === "Уведомления",
  })

  // Batch history query
  const { data: batchHistory, isLoading: batchLoading } = useQuery({
    queryKey: ["reminderBatches", telegramId],
    queryFn: () => getReminderBatches(telegramId!),
    enabled: activeTab === "Рассылки" && !!telegramId,
  })

  // Reminder mutations
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
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Уведомления</h2>

      {/* Tab buttons */}
      <div className="flex gap-1 border-b pb-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
              activeTab === tab
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab: Дашборд */}
      {activeTab === "Дашборд" && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <div>
              <label className="text-sm font-medium">Тип</label>
              <select
                className="ml-2 rounded-md border px-2 py-1 text-sm"
                value={dashType}
                onChange={(e) => setDashType(e.target.value)}
              >
                <option value="">Все</option>
                <option value="reminder">Напоминания</option>
                <option value="schedule_change">Изм. расписания</option>
                <option value="invitation">Приглашения</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">День</label>
              <Input
                type="date"
                className="ml-2 inline-block w-auto"
                value={dashDay}
                onChange={(e) => setDashDay(e.target.value)}
              />
            </div>
          </div>
          {dashLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {dashError && <p className="text-sm text-red-500">Ошибка загрузки дашборда</p>}
          {dashboard && (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{dashboard.summary.total}</div>
                    <p className="text-sm text-muted-foreground">Всего</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{dashboard.summary.sent}</div>
                    <p className="text-sm text-muted-foreground">Отправлено</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{dashboard.summary.failed}</div>
                    <p className="text-sm text-muted-foreground">Ошибок</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{dashboard.summary.pending}</div>
                    <p className="text-sm text-muted-foreground">Ожидает</p>
                  </CardContent>
                </Card>
              </div>

              {/* By role */}
              <Card>
                <CardHeader><CardTitle>По ролям</CardTitle></CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Роль</th>
                        <th className="py-2 pr-4">Отправлено</th>
                        <th className="py-2 pr-4">Ошибок</th>
                        <th className="py-2">Ожидает</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.by_role.map((r) => (
                        <tr key={r.role} className="border-b">
                          <td className="py-2 pr-4 font-medium">{r.role}</td>
                          <td className="py-2 pr-4">{r.sent}</td>
                          <td className="py-2 pr-4">{r.failed}</td>
                          <td className="py-2">{r.pending}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              {/* By type */}
              <Card>
                <CardHeader><CardTitle>По типам</CardTitle></CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Тип</th>
                        <th className="py-2 pr-4">Отправлено</th>
                        <th className="py-2 pr-4">Ошибок</th>
                        <th className="py-2">Ожидает</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.by_type.map((t) => (
                        <tr key={t.type} className="border-b">
                          <td className="py-2 pr-4 font-medium">{t.type}</td>
                          <td className="py-2 pr-4">{t.sent}</td>
                          <td className="py-2 pr-4">{t.failed}</td>
                          <td className="py-2">{t.pending}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              {/* Unreachable */}
              {dashboard.unreachable.length > 0 && (
                <Card>
                  <CardHeader><CardTitle>Недоступные участники</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-1">
                      {dashboard.unreachable.map((u) => (
                        <div key={u.user_id} className="text-sm">
                          <span className="font-medium">{u.name}</span>
                          <span className="text-muted-foreground"> ({u.role})</span>
                          <span className="text-xs text-red-500 ml-2">{u.reason}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab: Уведомления */}
      {activeTab === "Уведомления" && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <div>
              <label className="text-sm font-medium">Тип</label>
              <select
                className="ml-2 rounded-md border px-2 py-1 text-sm"
                value={notifType}
                onChange={(e) => { setNotifType(e.target.value); setNotifOffset(0) }}
              >
                <option value="">Все</option>
                <option value="reminder">Напоминания</option>
                <option value="schedule_change">Изм. расписания</option>
                <option value="invitation">Приглашения</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Статус</label>
              <select
                className="ml-2 rounded-md border px-2 py-1 text-sm"
                value={notifStatus}
                onChange={(e) => { setNotifStatus(e.target.value); setNotifOffset(0) }}
              >
                <option value="">Все</option>
                <option value="sent">Отправлено</option>
                <option value="failed">Ошибка</option>
                <option value="pending">Ожидает</option>
              </select>
            </div>
          </div>
          {notifLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {notifList && (
            <Card>
              <CardContent className="pt-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Пользователь</th>
                        <th className="py-2 pr-4">Тип</th>
                        <th className="py-2 pr-4">Статус</th>
                        <th className="py-2 pr-4">Запланировано</th>
                        <th className="py-2 pr-4">Отправлено</th>
                        <th className="py-2 pr-4">Ошибка</th>
                        <th className="py-2">Попыток</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notifList.items.map((n) => (
                        <tr key={n.id} className="border-b">
                          <td className="py-2 pr-4 font-medium">{n.user_name}</td>
                          <td className="py-2 pr-4">{n.type}</td>
                          <td className="py-2 pr-4">{statusBadge(n.status)}</td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(n.scheduled_at).toLocaleString("ru-RU")}
                          </td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                            {n.sent_at ? new Date(n.sent_at).toLocaleString("ru-RU") : "—"}
                          </td>
                          <td className="py-2 pr-4 text-xs text-red-500 max-w-xs truncate">
                            {n.error_message || "—"}
                          </td>
                          <td className="py-2">{n.retry_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex gap-2 mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={notifOffset === 0}
                    onClick={() => setNotifOffset(Math.max(0, notifOffset - notifLimit))}
                  >
                    Назад
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={notifList.items.length < notifLimit}
                    onClick={() => setNotifOffset(notifOffset + notifLimit)}
                  >
                    Далее
                  </Button>
                  <span className="text-xs text-muted-foreground self-center">
                    Всего: {notifList.total}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Tab: Рассылки */}
      {activeTab === "Рассылки" && (
        <div className="space-y-6">
          {/* Reminder Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Напоминания по расписанию</CardTitle>
            </CardHeader>
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

          {/* Batch History */}
          <Card>
            <CardHeader>
              <CardTitle>История рассылок</CardTitle>
            </CardHeader>
            <CardContent>
              {batchLoading && <p className="text-muted-foreground">Загрузка...</p>}
              {batchHistory && batchHistory.batches.length === 0 && (
                <p className="text-muted-foreground text-sm">Нет рассылок</p>
              )}
              {batchHistory && batchHistory.batches.length > 0 && (
                <div className="space-y-2">
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
                        <>
                          <tr
                            key={batch.id}
                            className="border-b cursor-pointer hover:bg-muted/50"
                            onClick={() => loadBatchDetail(batch.id)}
                          >
                            <td className="py-2 pr-4">{batch.reminder_type}</td>
                            <td className="py-2 pr-4">{statusBadge(batch.status)}</td>
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
                            <tr key={`${batch.id}-detail`}>
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
                        </>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
