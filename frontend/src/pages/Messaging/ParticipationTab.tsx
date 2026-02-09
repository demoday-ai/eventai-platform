import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import {
  broadcastParticipation,
  getParticipationSummary,
  getUnacknowledged,
  type BroadcastResult,
} from "../../lib/api-client"

export function ParticipationTab() {
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
