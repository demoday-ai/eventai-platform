import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { MessageSquare, Users } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import { useAuth } from "../hooks/useAuth"
import {
  getCoverage,
  getDashboard,
  isNoEventError,
  previewMessaging,
  sendMessaging,
  getNotificationDashboard,
  getNotifications,
  getScheduleReminderPreview,
  sendReminders,
  cancelReminders,
  getReminderBatches,
  getReminderBatchDetail,
  broadcastParticipation,
  getParticipationSummary,
  getUnacknowledged,
  getBriefingPreview,
  sendBriefing,
  type MessagingPreviewResponse,
  type MessagingSendResult,
  type ScheduleReminderPreview,
  type ReminderSendResult,
  type ReminderCancelResult,
  type ReminderBatchDetail,
  type BroadcastResult,
  type BriefingPreview as BriefingPreviewType,
  type BriefingSendResult,
} from "../lib/api-client"

const TABS = ["Обзор", "Рассылка", "Напоминания", "Участие", "Брифинг"] as const
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

export function Messaging() {
  const [activeTab, setActiveTab] = useState<Tab>("Обзор")

  useEffect(() => {
    document.title = `${APP_NAME} - Рассылки`
  }, [])

  // Check for event and participants
  const { data: dashboardData, error: dashboardError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    retry: false,
  })

  // Tier 1: No event
  if (dashboardError && isNoEventError(dashboardError)) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Рассылки</h2>
        <PageEmptyState
          icon={MessageSquare}
          title="Создайте мероприятие"
          description="Создайте мероприятие на странице Импорта, чтобы начать рассылки."
          actionLabel="Перейти к импорту"
          actionLink="/import"
        />
      </div>
    )
  }

  // Tier 2: No participants
  if (dashboardData) {
    const totalParticipants =
      (dashboardData.students?.total || 0) +
      (dashboardData.experts?.total || 0) +
      (dashboardData.guests?.total || 0) +
      (dashboardData.partners?.total || 0)

    if (totalParticipants === 0) {
      return (
        <div className="grid gap-6">
          <h2 className="text-2xl font-bold">Рассылки</h2>
          <PageEmptyState
            icon={Users}
            title="Загрузите участников"
            description="Загрузите участников на странице Импорта, чтобы начать рассылки."
            actionLabel="Перейти к импорту"
            actionLink="/import"
          />
        </div>
      )
    }
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Рассылки</h2>

      {/* Tabs */}
      <div className="flex gap-1 border-b pb-0 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors whitespace-nowrap ${
              activeTab === tab
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Обзор" && <OverviewTab />}
      {activeTab === "Рассылка" && <BroadcastTab />}
      {activeTab === "Напоминания" && <RemindersTab />}
      {activeTab === "Участие" && <ParticipationTab />}
      {activeTab === "Брифинг" && <BriefingTab />}
    </div>
  )
}

// =============================================================================
// Tab: Обзор (from Notifications dashboard + notification list)
// =============================================================================

function OverviewTab() {
  const [dashType, setDashType] = useState("")
  const [dashDay, setDashDay] = useState("")
  const [notifType, setNotifType] = useState("")
  const [notifStatus, setNotifStatus] = useState("")
  const [notifOffset, setNotifOffset] = useState(0)
  const notifLimit = 20

  const { data: dashboard, isLoading: dashLoading, isError: dashError } = useQuery({
    queryKey: ["notificationDashboard", dashType, dashDay],
    queryFn: () =>
      getNotificationDashboard({
        type: dashType || undefined,
        day: dashDay || undefined,
      }),
  })

  const { data: notifList, isLoading: notifLoading } = useQuery({
    queryKey: ["notifications", notifType, notifStatus, notifOffset],
    queryFn: () =>
      getNotifications({
        type: notifType || undefined,
        status: notifStatus || undefined,
        offset: notifOffset,
        limit: notifLimit,
      }),
  })

  return (
    <div className="space-y-6">
      {/* Dashboard */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Статистика</h3>
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
            <label className="text-sm font-medium">Тип</label>
            <select
              className="rounded-md border px-2 py-1.5 text-sm"
              value={dashType}
              onChange={(e) => setDashType(e.target.value)}
            >
              <option value="">Все</option>
              <option value="reminder">Напоминания</option>
              <option value="schedule_change">Изм. расписания</option>
              <option value="invitation">Приглашения</option>
            </select>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
            <label className="text-sm font-medium">День</label>
            <Input
              type="date"
              className="w-full sm:w-auto"
              value={dashDay}
              onChange={(e) => setDashDay(e.target.value)}
            />
          </div>
        </div>
        {dashLoading && <p className="text-muted-foreground">Загрузка...</p>}
        {dashError && <p className="text-sm text-red-500">Ошибка загрузки дашборда</p>}
        {dashboard && (
          <>
            <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
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

            <div className="grid gap-4 lg:grid-cols-2">
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
            </div>

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

      {/* Notification List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">История уведомлений</h3>
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
    </div>
  )
}

// =============================================================================
// Tab: Рассылка (broadcast messaging)
// =============================================================================

const ROLE_OPTIONS = [
  { code: "student", label: "Студенты" },
  { code: "expert", label: "Эксперты" },
  { code: "guest", label: "Гости" },
  { code: "business", label: "Бизнес-партнёры" },
]

const GUEST_SUBTYPES = [
  { value: "investor", label: "Инвесторы" },
  { value: "business_partner", label: "Бизнес-партнёры" },
  { value: "mentor", label: "Менторы" },
  { value: "hr", label: "HR" },
  { value: "jury", label: "Жюри" },
  { value: "student", label: "Студенты" },
  { value: "applicant", label: "Абитуриенты" },
  { value: "other", label: "Другое" },
]

function BroadcastTab() {
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [guestSubtype, setGuestSubtype] = useState<string>("")
  const [roomId, setRoomId] = useState<string>("")
  const [template, setTemplate] = useState("")
  const [preview, setPreview] = useState<MessagingPreviewResponse | null>(null)
  const [sendResult, setSendResult] = useState<MessagingSendResult | null>(null)

  const { data: rooms } = useQuery({
    queryKey: ["coverage"],
    queryFn: getCoverage,
    enabled: selectedRoles.includes("expert"),
  })

  const previewMutation = useMutation({
    mutationFn: previewMessaging,
    onSuccess: (data) => {
      setPreview(data)
      setSendResult(null)
    },
  })

  const sendMutation = useMutation({
    mutationFn: sendMessaging,
    onSuccess: (data) => setSendResult(data),
  })

  const toggleRole = (code: string) => {
    setSelectedRoles((prev) =>
      prev.includes(code) ? prev.filter((r) => r !== code) : [...prev, code]
    )
    setPreview(null)
    setSendResult(null)
  }

  const canPreview = selectedRoles.length > 0 && template.trim().length > 0

  const handlePreview = () => {
    previewMutation.mutate({
      template,
      roles: selectedRoles,
      guest_subtype: selectedRoles.includes("guest") && guestSubtype ? guestSubtype : null,
      room_id: selectedRoles.includes("expert") && roomId ? roomId : null,
    })
  }

  const handleSend = () => {
    sendMutation.mutate({
      template,
      roles: selectedRoles,
      guest_subtype: selectedRoles.includes("guest") && guestSubtype ? guestSubtype : null,
      room_id: selectedRoles.includes("expert") && roomId ? roomId : null,
    })
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Аудитория</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            {ROLE_OPTIONS.map((role) => (
              <label key={role.code} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedRoles.includes(role.code)}
                  onChange={() => toggleRole(role.code)}
                  className="rounded"
                />
                {role.label}
              </label>
            ))}
          </div>
          {selectedRoles.includes("guest") && (
            <div className="space-y-2">
              <Label htmlFor="guest-subtype">Подтип гостей</Label>
              <Select value={guestSubtype} onValueChange={setGuestSubtype}>
                <SelectTrigger id="guest-subtype">
                  <SelectValue placeholder="Все подтипы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все подтипы</SelectItem>
                  {GUEST_SUBTYPES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          {selectedRoles.includes("expert") && rooms && (
            <div className="space-y-2">
              <Label htmlFor="room-filter">Зал</Label>
              <Select value={roomId} onValueChange={setRoomId}>
                <SelectTrigger id="room-filter">
                  <SelectValue placeholder="Все залы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все залы</SelectItem>
                  {rooms.map((room) => (
                    <SelectItem key={room.room_id} value={room.room_id}>{room.room_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Сообщение</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="template">Текст сообщения</Label>
            <textarea
              id="template"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Здравствуйте, {name}! ..."
              value={template}
              onChange={(e) => {
                setTemplate(e.target.value)
                setPreview(null)
                setSendResult(null)
              }}
            />
            <p className="text-xs text-muted-foreground">
              Используйте {"{name}"} для подстановки имени получателя.
            </p>
          </div>
          <Button onClick={handlePreview} disabled={!canPreview || previewMutation.isPending}>
            {previewMutation.isPending ? "Загрузка..." : "Предпросмотр"}
          </Button>
          {previewMutation.isError && (
            <p className="text-sm text-red-500">
              Ошибка: {previewMutation.error instanceof Error ? previewMutation.error.message : "Неизвестная ошибка"}
            </p>
          )}
        </CardContent>
      </Card>

      {preview && !sendResult && (
        <Card>
          <CardHeader><CardTitle>Предпросмотр</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm">
              <p className="text-muted-foreground">Получателей</p>
              <p className="text-2xl font-bold">{preview.recipient_count}</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Пример сообщения:</p>
              <div className="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
                {preview.sample_message}
              </div>
            </div>
            {preview.recipients_preview.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Получатели (первые {preview.recipients_preview.length}):</p>
                <ul className="text-sm space-y-1">
                  {preview.recipients_preview.map((r) => (
                    <li key={r.user_id} className="text-muted-foreground">
                      {r.full_name} ({r.role}{r.guest_subtype ? `, ${r.guest_subtype}` : ""})
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <Button onClick={handleSend} disabled={sendMutation.isPending || preview.recipient_count === 0}>
              {sendMutation.isPending ? "Отправка..." : `Отправить (${preview.recipient_count})`}
            </Button>
            {sendMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка отправки: {sendMutation.error instanceof Error ? sendMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {sendResult && (
        <Card className="border-green-300">
          <CardHeader><CardTitle>Результат рассылки</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Отправлено</p>
                <p className="text-2xl font-bold text-green-600">{sendResult.sent}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Ошибки</p>
                <p className="text-2xl font-bold text-red-600">{sendResult.failed}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Пропущено</p>
                <p className="text-2xl font-bold text-yellow-600">{sendResult.skipped}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// =============================================================================
// Tab: Напоминания (schedule reminders + batch history)
// =============================================================================

function RemindersTab() {
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
  )
}

// =============================================================================
// Tab: Участие (participation confirmation)
// =============================================================================

function ParticipationTab() {
  const [roomFilter, setRoomFilter] = useState<string>("")
  const [broadcastResult, setBroadcastResult] = useState<BroadcastResult | null>(null)

  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
    queryKey: ["participationSummary", roomFilter],
    queryFn: () => getParticipationSummary(roomFilter || undefined),
    refetchInterval: 60000,
  })

  const { data: unacknowledged, isLoading: unackLoading } = useQuery({
    queryKey: ["unacknowledged", roomFilter],
    queryFn: () => getUnacknowledged(roomFilter || undefined),
    refetchInterval: 60000,
  })

  const broadcastMutation = useMutation({
    mutationFn: broadcastParticipation,
    onSuccess: (data) => setBroadcastResult(data),
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Рассылка подтверждения участия</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Button onClick={() => broadcastMutation.mutate()} disabled={broadcastMutation.isPending}>
            {broadcastMutation.isPending ? "Отправка..." : "Отправить рассылку"}
          </Button>
          {broadcastMutation.isError && (
            <p className="text-sm text-red-500">Ошибка отправки рассылки</p>
          )}
          {broadcastResult && (
            <div className="text-sm space-y-1">
              <p>Отправлено: {broadcastResult.sent}</p>
              <p>Пропущено: {broadcastResult.skipped}</p>
              <p>Ошибок: {broadcastResult.failed}</p>
              <p>Незарегистрированных: {broadcastResult.unregistered}</p>
              {broadcastResult.unregistered_projects.length > 0 && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-muted-foreground">
                    Незарегистрированные проекты ({broadcastResult.unregistered_projects.length})
                  </summary>
                  <ul className="mt-1 list-disc pl-4 text-xs text-muted-foreground">
                    {broadcastResult.unregistered_projects.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Сводка</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {summaryLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {summaryError && <p className="text-sm text-red-500">Ошибка загрузки</p>}
          {summary && (
            <>
              <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.total}</div>
                    <p className="text-sm text-muted-foreground">Всего</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.acknowledged}</div>
                    <p className="text-sm text-muted-foreground">Подтверждено</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.pending}</div>
                    <p className="text-sm text-muted-foreground">Ожидает</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.unregistered}</div>
                    <p className="text-sm text-muted-foreground">Незарегистрированных</p>
                  </CardContent>
                </Card>
              </div>

              {summary.by_room.length > 0 && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Фильтр по залу</label>
                  <select
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    value={roomFilter}
                    onChange={(e) => setRoomFilter(e.target.value)}
                  >
                    <option value="">Все залы</option>
                    {summary.by_room.map((r) => (
                      <option key={r.room_id} value={r.room_id}>{r.room_name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 pr-4">Зал</th>
                      <th className="py-2 pr-4">Всего</th>
                      <th className="py-2 pr-4">Подтв.</th>
                      <th className="py-2">Ожидает</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_room.map((r) => (
                      <tr key={r.room_id} className="border-b">
                        <td className="py-2 pr-4 font-medium">{r.room_name}</td>
                        <td className="py-2 pr-4">{r.total}</td>
                        <td className="py-2 pr-4">{r.acknowledged}</td>
                        <td className="py-2">{r.pending}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Неподтверждённые</CardTitle></CardHeader>
        <CardContent>
          {unackLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {unacknowledged && unacknowledged.items.length === 0 && (
            <p className="text-muted-foreground text-sm">Все участники подтвердили</p>
          )}
          {unacknowledged && unacknowledged.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-4">Проект</th>
                    <th className="py-2 pr-4">Автор</th>
                    <th className="py-2 pr-4">Telegram</th>
                    <th className="py-2 pr-4">Зал</th>
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Отправлено</th>
                    <th className="py-2 pr-4">Напоминание</th>
                    <th className="py-2">Эскалация</th>
                  </tr>
                </thead>
                <tbody>
                  {unacknowledged.items.map((item) => (
                    <tr key={item.request_id} className="border-b">
                      <td className="py-2 pr-4 font-medium">{item.project_title}</td>
                      <td className="py-2 pr-4">{item.author_name}</td>
                      <td className="py-2 pr-4 text-xs">{item.telegram_contact}</td>
                      <td className="py-2 pr-4">{item.room_name}</td>
                      <td className="py-2 pr-4">{item.status}</td>
                      <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(item.sent_at).toLocaleString("ru-RU")}
                      </td>
                      <td className="py-2 pr-4">
                        {item.reminder_sent ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">Да</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Нет</span>
                        )}
                      </td>
                      <td className="py-2">
                        {item.escalated ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">Да</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Нет</span>
                        )}
                      </td>
                    </tr>
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

// =============================================================================
// Tab: Брифинг (expert briefings)
// =============================================================================

function BriefingTab() {
  const [preview, setPreview] = useState<BriefingPreviewType | null>(null)
  const [sendResult, setSendResult] = useState<BriefingSendResult | null>(null)

  const previewMutation = useMutation({
    mutationFn: getBriefingPreview,
    onSuccess: (data) => setPreview(data),
  })

  const sendMutation = useMutation({
    mutationFn: sendBriefing,
    onSuccess: (data) => setSendResult(data),
  })

  const is404 =
    previewMutation.isError &&
    previewMutation.error instanceof Error &&
    previewMutation.error.message.includes("404")

  return (
    <div className="space-y-6">
      {!preview && !sendResult && (
        <Card>
          <CardHeader><CardTitle>Брифинг экспертов</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Загрузите предпросмотр, чтобы увидеть, сколько экспертов получат брифинг.
            </p>
            <Button onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>
              {previewMutation.isPending ? "Загрузка..." : "Предпросмотр"}
            </Button>
            {is404 && (
              <p className="text-sm text-red-500">
                Нет одобренной кластеризации. Сначала одобрите кластеризацию и матчинг.
              </p>
            )}
            {previewMutation.isError && !is404 && (
              <p className="text-sm text-red-500">
                Ошибка: {previewMutation.error instanceof Error ? previewMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {preview && !sendResult && (
        <Card>
          <CardHeader><CardTitle>Предпросмотр брифинга</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Всего экспертов</p>
                <p className="text-2xl font-bold">{preview.expert_count}</p>
              </div>
              <div>
                <p className="text-muted-foreground">С Telegram</p>
                <p className="text-2xl font-bold text-green-600">{preview.with_telegram}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Без Telegram</p>
                <p className="text-2xl font-bold text-yellow-600">{preview.without_telegram}</p>
              </div>
            </div>
            <Button onClick={() => sendMutation.mutate()} disabled={sendMutation.isPending}>
              {sendMutation.isPending ? "Отправка..." : "Отправить брифинги"}
            </Button>
            {sendMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка отправки: {sendMutation.error instanceof Error ? sendMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {sendResult && (
        <Card className="border-green-300">
          <CardHeader><CardTitle>Брифинги отправлены</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Отправлено</p>
                <p className="text-2xl font-bold text-green-600">{sendResult.sent}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Ошибки</p>
                <p className="text-2xl font-bold text-red-600">{sendResult.failed}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Пропущено</p>
                <p className="text-2xl font-bold text-yellow-600">{sendResult.skipped}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
