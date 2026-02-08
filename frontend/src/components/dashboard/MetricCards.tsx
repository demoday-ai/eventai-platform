import type { ReactNode } from "react"
import { FolderKanban, GraduationCap, Users, Handshake, Building2, CheckCircle, Clock, XCircle } from "lucide-react"
import { Card, CardContent } from "../ui/card"
import { Skeleton } from "../ui/skeleton"
import type { DashboardData } from "../../lib/api-client"

interface MetricCardProps {
  title: string
  value: string
  subtitle: ReactNode
  icon: ReactNode
  loading?: boolean
}

function MetricCard({ title, value, subtitle, icon, loading }: MetricCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-3 md:pt-6 md:p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-12" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-6 rounded-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-3 md:pt-6 md:p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs md:text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl md:text-3xl font-bold mt-1">{value}</p>
            <p className="text-[10px] md:text-xs text-muted-foreground mt-1 truncate">{subtitle}</p>
          </div>
          <span>{icon}</span>
        </div>
      </CardContent>
    </Card>
  )
}

interface MetricCardsProps {
  data: DashboardData | undefined
  loading: boolean
}

export function MetricCards({ data, loading }: MetricCardsProps) {
  const iconClass = "w-5 h-5 md:w-6 md:h-6 text-muted-foreground"

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 md:gap-4">
      <MetricCard
        title="Проекты"
        value={loading ? "—" : String(data?.projects.total ?? 0)}
        subtitle={loading ? "Загрузка..." : "Всего проектов"}
        icon={<FolderKanban className={iconClass} />}
        loading={loading}
      />
      <MetricCard
        title="Студенты"
        value={loading ? "—" : String(data?.students.total ?? 0)}
        subtitle={
          loading ? "Загрузка..." : (
            <span className="inline-flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-600" />{data?.students.confirmed}
              {" | "}
              <Clock className="w-3 h-3 text-yellow-600" />{data?.students.pending}
              {" | "}
              <XCircle className="w-3 h-3 text-red-600" />{data?.students.declined}
            </span>
          )
        }
        icon={<GraduationCap className={iconClass} />}
        loading={loading}
      />
      <MetricCard
        title="Эксперты"
        value={loading ? "—" : String(data?.experts.total ?? 0)}
        subtitle={
          loading ? "Загрузка..." : (
            <span className="inline-flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-600" />{data?.experts.confirmed}
              {" | "}
              <Clock className="w-3 h-3 text-yellow-600" />{data?.experts.pending}
            </span>
          )
        }
        icon={<Users className={iconClass} />}
        loading={loading}
      />
      <MetricCard
        title="Партнёры"
        value={loading ? "—" : String(data?.partners.total ?? 0)}
        subtitle={
          loading ? "Загрузка..." : (
            <span className="inline-flex items-center gap-1">
              Бот: {data?.partners.from_bot} | Импорт: {data?.partners.from_import}
            </span>
          )
        }
        icon={<Handshake className={iconClass} />}
        loading={loading}
      />
      <MetricCard
        title="Залы"
        value={loading ? "—" : String(data?.rooms.total ?? 0)}
        subtitle={
          loading ? "Загрузка..." : (
            <span className="inline-flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-600" />{data?.rooms.with_experts}
              {" | "}
              <XCircle className="w-3 h-3 text-red-600" />{data?.rooms.without_experts}
            </span>
          )
        }
        icon={<Building2 className={iconClass} />}
        loading={loading}
      />
    </div>
  )
}
