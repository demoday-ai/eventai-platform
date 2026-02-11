import { useEffect } from "react"
import { useQuery, keepPreviousData } from "@tanstack/react-query"
import { RefreshCw, AlertTriangle, AlertCircle, Info } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { APP_NAME } from "../lib/constants"
import { getDashboard, getCoverage, type DashboardData, type RoomCoverage, type Alert as AlertType } from "../lib/api-client"
import { EmptyState } from "../components/dashboard/EmptyState"
import { QuickAction } from "../components/dashboard/QuickAction"
import { MetricCards } from "../components/dashboard/MetricCards"
import { EventCountdown } from "../components/dashboard/EventCountdown"
import { DashboardCoverageTable } from "../components/dashboard/CoverageTable"
import { startAdminTour, shouldShowTour } from "../lib/adminTour"

export function Dashboard() {
  useEffect(() => {
    document.title = `${APP_NAME} - Dashboard`
  }, [])

  const {
    data,
    isLoading,
    error,
    refetch,
    dataUpdatedAt,
  } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    refetchInterval: 30_000,
    placeholderData: keepPreviousData,
  })

  // Auto-start tour on first visit (after data loads)
  useEffect(() => {
    if (data && !isLoading && shouldShowTour()) {
      // Delay to ensure UI is fully rendered
      const timer = setTimeout(() => {
        startAdminTour()
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [data, isLoading])

  const {
    data: coverageData,
    isLoading: coverageLoading,
  } = useQuery<RoomCoverage[]>({
    queryKey: ["coverage"],
    queryFn: getCoverage,
    refetchInterval: 30_000,
    placeholderData: keepPreviousData,
  })

  const formatLastUpdate = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  }

  // Empty state: no event
  const hasNoEvent = !isLoading && data && !data.event

  return (
    <div className="grid gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex items-center gap-3">
          {dataUpdatedAt > 0 && (
            <span className="text-xs text-muted-foreground">
              Обновлено: {formatLastUpdate(dataUpdatedAt)}
            </span>
          )}
          <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Empty state */}
      {hasNoEvent && <EmptyState />}

      {/* Error state */}
      {error && (
        <Card className="border-red-500">
          <CardContent className="pt-6">
            <p className="text-red-500">
              Ошибка загрузки данных: {error instanceof Error ? error.message : "Неизвестная ошибка"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Main content: only when event exists */}
      {!hasNoEvent && !error && (
        <>
          {/* Event countdown */}
          {data?.event && <EventCountdown event={data.event} />}

          {/* Quick Action */}
          <QuickAction />

          {/* Metric cards */}
          <MetricCards data={data} loading={isLoading} />

          {/* Alerts */}
          {data?.alerts && data.alerts.length > 0 && (
            <AlertsCard alerts={data.alerts} />
          )}

          {/* Coverage table */}
          {!coverageLoading && coverageData && coverageData.length > 0 && (
            <DashboardCoverageTable data={coverageData} />
          )}
        </>
      )}
    </div>
  )
}

function AlertsCard({ alerts }: { alerts: AlertType[] }) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-50 border-red-200 text-red-900"
      case "warning":
        return "bg-yellow-50 border-yellow-200 text-yellow-900"
      default:
        return "bg-blue-50 border-blue-200 text-blue-900"
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertTriangle className="w-5 h-5 text-red-600" />
      case "warning":
        return <AlertCircle className="w-5 h-5 text-yellow-600" />
      default:
        return <Info className="w-5 h-5 text-blue-600" />
    }
  }

  return (
    <Card className="border-orange-200">
      <CardHeader>
        <CardTitle>Алерты</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {alerts.map((alert, idx) => {
            const content = (
              <div className="flex items-start gap-2">
                <span className="shrink-0">{getSeverityIcon(alert.severity)}</span>
                <div className="flex-1">
                  <p className="font-medium">{alert.message}</p>
                  {alert.room_name && (
                    <p className="text-sm opacity-75 mt-1">
                      Зал: {alert.room_name}
                    </p>
                  )}
                </div>
                {alert.link && (
                  <button className="text-sm underline opacity-75 hover:opacity-100">
                    Перейти
                  </button>
                )}
              </div>
            )

            if (alert.link) {
              return (
                <a
                  key={idx}
                  href={alert.link}
                  className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)} hover:opacity-90 transition-opacity block`}
                >
                  {content}
                </a>
              )
            }

            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}
              >
                {content}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
