import { useAuth } from "../hooks/useAuth"
import { useNavigate } from "react-router-dom"
import { Button } from "../components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { APP_NAME } from "../lib/constants"

export function Dashboard() {
  const { telegramId, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">{APP_NAME}</h1>
          <div className="flex items-center gap-4">
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
                Добро пожаловать в панель управления Demo Day.
              </p>
              <p className="text-muted-foreground mt-2">
                Здесь будут отображаться метрики, покрытие залов и алерты.
              </p>
            </CardContent>
          </Card>

          {/* Placeholder metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Студенты"
              value="—"
              subtitle="Загрузка..."
              icon="📋"
            />
            <MetricCard
              title="Эксперты"
              value="—"
              subtitle="Загрузка..."
              icon="👨‍🏫"
            />
            <MetricCard
              title="Гости"
              value="—"
              subtitle="Загрузка..."
              icon="👥"
            />
            <MetricCard
              title="Залы"
              value="—"
              subtitle="Загрузка..."
              icon="🏠"
            />
          </div>

          {/* Placeholder for coverage table */}
          <Card>
            <CardHeader>
              <CardTitle>Покрытие залов</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                Таблица покрытия будет здесь
              </div>
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
}: {
  title: string
  value: string
  subtitle: string
  icon: string
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
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
