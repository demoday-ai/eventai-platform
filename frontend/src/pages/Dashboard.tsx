import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "../hooks/useAuth"
import { useNavigate } from "react-router-dom"
import { Button } from "../components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Skeleton } from "../components/ui/skeleton"
import { APP_NAME } from "../lib/constants"
import { getDashboard, getCoverage, type DashboardData, type Alert as AlertType } from "../lib/api-client"
import { CoverageTable } from "../components/CoverageTable"

export function Dashboard() {
  const { telegramId, logout } = useAuth()
  const navigate = useNavigate()

  // Set page title
  useEffect(() => {
    document.title = `${APP_NAME} - Dashboard`
  }, [])

  // Fetch dashboard data with auto-refresh every 60 seconds
  const {
    data,
    isLoading,
    error,
    refetch,
    dataUpdatedAt,
  } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    refetchInterval: 60000, // 60 seconds
  })

  // Fetch coverage data
  const {
    data: coverageData,
    isLoading: coverageLoading,
  } = useQuery({
    queryKey: ["coverage"],
    queryFn: getCoverage,
    refetchInterval: 60000,
  })

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  const handleRefresh = () => {
    refetch()
  }

  const formatLastUpdate = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">{APP_NAME}</h1>
          <div className="flex items-center gap-4">
            {dataUpdatedAt && (
              <span className="text-xs text-muted-foreground">
                Обновлено: {formatLastUpdate(dataUpdatedAt)}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={isLoading}>
              🔄
            </Button>
            <span className="text-sm text-muted-foreground">
              ID: {telegramId}
            </span>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Выйти
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6">
          {/* Welcome card */}
          <Card>
            <CardHeader>
              <CardTitle>Demo Day 2026</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Панель управления Demo Day. Статистика обновляется автоматически каждую минуту.
              </p>
            </CardContent>
          </Card>

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

          {/* Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Студенты"
              value={isLoading ? "—" : data?.students.total.toString() || "0"}
              subtitle={
                isLoading
                  ? "Загрузка..."
                  : `✓ ${data?.students.confirmed} | ⏳ ${data?.students.pending} | ✗ ${data?.students.declined}`
              }
              icon="📋"
              loading={isLoading}
            />
            <MetricCard
              title="Эксперты"
              value={isLoading ? "—" : data?.experts.total.toString() || "0"}
              subtitle={
                isLoading
                  ? "Загрузка..."
                  : `✓ ${data?.experts.confirmed} | ⏳ ${data?.experts.pending}`
              }
              icon="👨‍🏫"
              loading={isLoading}
            />
            <MetricCard
              title="Гости"
              value={isLoading ? "—" : data?.guests.total.toString() || "0"}
              subtitle={
                isLoading
                  ? "Загрузка..."
                  : data?.guests.by_subtype.map((s) => `${s.subtype}: ${s.count}`).join(" | ") || "Нет данных"
              }
              icon="👥"
              loading={isLoading}
            />
            <MetricCard
              title="Залы"
              value={isLoading ? "—" : data?.rooms.total.toString() || "0"}
              subtitle={
                isLoading
                  ? "Загрузка..."
                  : `🟢 ${data?.rooms.with_experts} | 🔴 ${data?.rooms.without_experts}`
              }
              icon="🏠"
              loading={isLoading}
            />
          </div>

          {/* Alerts */}
          {data?.alerts && data.alerts.length > 0 && (
            <AlertsCard alerts={data.alerts} />
          )}

          {/* Coverage table */}
          <Card>
            <CardHeader>
              <CardTitle>Покрытие залов</CardTitle>
            </CardHeader>
            <CardContent>
              {coverageLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Загрузка...
                </div>
              ) : (
                <CoverageTable data={coverageData || []} />
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  loading,
}: {
  title: string
  value: string
  subtitle: string
  icon: string
  loading?: boolean
}) {
  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-16" />
              <Skeleton className="h-3 w-32" />
            </div>
            <Skeleton className="h-8 w-8 rounded-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          </div>
          <span className="text-2xl">{icon}</span>
        </div>
      </CardContent>
    </Card>
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
        return "🚨"
      case "warning":
        return "⚠️"
      default:
        return "ℹ️"
    }
  }

  return (
    <Card className="border-orange-200">
      <CardHeader>
        <CardTitle>Алерты</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg">{getSeverityIcon(alert.severity)}</span>
                <div className="flex-1">
                  <p className="font-medium">{alert.message}</p>
                  {alert.room_name && (
                    <p className="text-sm opacity-75 mt-1">
                      Зал: {alert.room_name}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
