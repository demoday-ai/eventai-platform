import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Bell, Users } from "lucide-react"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import { getDashboard, isNoEventError } from "../lib/api-client"
import { RemindersTab } from "./Messaging/RemindersTab"

export function Reminders() {
  useEffect(() => {
    document.title = `${APP_NAME} - Авто-напоминания`
  }, [])

  const { data: dashboardData, error: dashboardError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    retry: false,
  })

  if (dashboardError && isNoEventError(dashboardError)) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Авто-напоминания</h2>
        <PageEmptyState
          icon={Bell}
          title="Создайте мероприятие"
          description="Создайте мероприятие, чтобы настроить напоминания."
          actionLabel="Перейти к мероприятию"
          actionLink="/event"
        />
      </div>
    )
  }

  if (dashboardData) {
    const totalParticipants =
      (dashboardData.students?.total || 0) +
      (dashboardData.experts?.total || 0) +
      (dashboardData.guests?.total || 0) +
      (dashboardData.partners?.total || 0)

    if (totalParticipants === 0) {
      return (
        <div className="grid gap-6">
          <h2 className="text-2xl font-bold">Авто-напоминания</h2>
          <PageEmptyState
            icon={Users}
            title="Загрузите участников"
            description="Загрузите участников на странице Импорта, чтобы настроить напоминания."
            actionLabel="Перейти к импорту"
            actionLink="/import"
          />
        </div>
      )
    }
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Авто-напоминания</h2>
      <RemindersTab />
    </div>
  )
}
