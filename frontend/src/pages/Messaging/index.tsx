import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { MessageSquare, Users } from "lucide-react"
import { PageEmptyState } from "../../components/ui/PageEmptyState"
import { APP_NAME } from "../../lib/constants"
import { getDashboard, isNoEventError } from "../../lib/api-client"
import { OverviewTab } from "./OverviewTab"
import { BroadcastTab } from "./BroadcastTab"
import { ParticipationTab } from "./ParticipationTab"
import { BriefingTab } from "./BriefingTab"
import { RemindersTab } from "./RemindersTab"

const TABS = ["Обзор", "Рассылка", "Участие", "Брифинг", "Напоминания"] as const
type Tab = (typeof TABS)[number]

export function Messaging() {
  const [activeTab, setActiveTab] = useState<Tab>("Обзор")

  useEffect(() => {
    document.title = `${APP_NAME} - Рассылки`
  }, [])

  const { data: dashboardData, error: dashboardError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    retry: false,
  })

  if (dashboardError && isNoEventError(dashboardError)) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Рассылки</h2>
        <PageEmptyState
          icon={MessageSquare}
          title="Создайте мероприятие"
          description="Создайте мероприятие, чтобы начать рассылки."
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

      {activeTab !== "Обзор" && (
        <p className="text-sm text-muted-foreground -mt-2">
          {activeTab === "Рассылка" && "Ручная массовая отправка сообщений участникам"}
          {activeTab === "Участие" && "Управление участием и сегментами аудитории"}
          {activeTab === "Брифинг" && "Автоматический персональный пакет эксперту перед Demo Day: зал, проекты, описания, время"}
          {activeTab === "Напоминания" && "Автоматические уведомления за день и за 30 минут до выступления"}
        </p>
      )}

      {activeTab === "Обзор" && <OverviewTab />}
      {activeTab === "Рассылка" && <BroadcastTab />}
      {activeTab === "Участие" && <ParticipationTab />}
      {activeTab === "Брифинг" && <BriefingTab />}
      {activeTab === "Напоминания" && <RemindersTab />}
    </div>
  )
}
