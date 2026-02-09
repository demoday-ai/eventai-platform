import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import { StatusBadge } from "../../components/shared/StatusBadge"
import {
  getNotificationDashboard,
  getNotifications,
} from "../../lib/api-client"

export function OverviewTab() {
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
                        <td className="py-2 pr-4"><StatusBadge status={n.status} variant="notification" /></td>
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
