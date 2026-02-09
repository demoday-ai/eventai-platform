import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Label } from "../components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { APP_NAME } from "../lib/constants"
import { getAuditLog, type AuditLogItem } from "../lib/api-client"

const ACTION_LABELS: Record<string, string> = {
  event_update: "Обновление события",
  upload_projects: "Загрузка проектов",
  upload_experts: "Загрузка экспертов",
  upload_guests: "Загрузка гостей",
  send_briefing: "Отправка брифинга",
  send_messaging: "Отправка рассылки",
  schedule_generate: "Генерация расписания",
  schedule_approve: "Утверждение расписания",
  slot_update: "Изменение слота",
}

export function AuditLog() {
  const [actionFilter, setActionFilter] = useState("")

  useEffect(() => {
    document.title = `${APP_NAME} - Журнал действий`
  }, [])

  const { data: auditData, isLoading } = useQuery({
    queryKey: ["auditLog", actionFilter],
    queryFn: () => getAuditLog({ action: actionFilter && actionFilter !== "all" ? actionFilter : undefined, limit: 50 }),
  })

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Журнал действий</h2>

      <Card>
        <CardHeader>
          <CardTitle>История операций</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="audit-action-filter">Фильтр по действию</Label>
            <Select value={actionFilter} onValueChange={setActionFilter}>
              <SelectTrigger id="audit-action-filter" className="w-[220px]">
                <SelectValue placeholder="Все действия" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все действия</SelectItem>
                {Object.entries(ACTION_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {isLoading && <p className="text-muted-foreground">Загрузка...</p>}

          {auditData && auditData.items.length === 0 && (
            <p className="text-muted-foreground">Нет записей</p>
          )}

          {auditData && auditData.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 pr-4">Время</th>
                    <th className="text-left py-2 pr-4">Пользователь</th>
                    <th className="text-left py-2 pr-4">Действие</th>
                    <th className="text-left py-2">Объект</th>
                  </tr>
                </thead>
                <tbody>
                  {auditData.items.map((item: AuditLogItem) => (
                    <tr key={item.id} className="border-b">
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {new Date(item.created_at).toLocaleString("ru-RU")}
                      </td>
                      <td className="py-2 pr-4">{item.user_name || "—"}</td>
                      <td className="py-2 pr-4">{ACTION_LABELS[item.action] || item.action}</td>
                      <td className="py-2">
                        {item.entity_type || "—"}
                        {item.entity_id ? ` #${item.entity_id.slice(0, 8)}` : ""}
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
