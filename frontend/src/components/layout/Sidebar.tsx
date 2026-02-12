import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  CalendarDays,
  Upload,
  Tag,
  Layers,
  Users,
  UsersRound,
  Calendar,
  FolderOpen,
  MessageSquare,
  UserCheck,
  Settings,
  ClipboardList,
  type LucideIcon,
} from "lucide-react"
import { cn } from "../../lib/utils"
import { usePipelineStatus } from "../../hooks/usePipelineStatus"
import type { PipelineStep } from "../../lib/api-client"

type BadgeStatus = "completed" | "attention" | "not_started" | null

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Pipeline step names to derive badge status from */
  pipelineSteps?: string[]
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    label: "Подготовка",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/event", label: "Мероприятие", icon: CalendarDays, pipelineSteps: ["event"] },
      { to: "/import", label: "Импорт данных", icon: Upload, pipelineSteps: ["projects", "students", "experts"] },
      { to: "/tags", label: "Теги", icon: Tag },
      { to: "/projects", label: "Проекты", icon: FolderOpen },
      { to: "/participants", label: "Участники", icon: UsersRound },
    ],
  },
  {
    label: "Распределение",
    items: [
      { to: "/clustering", label: "Кластеризация", icon: Layers, pipelineSteps: ["clustering"] },
      { to: "/experts", label: "Эксперты", icon: Users, pipelineSteps: ["matching"] },
      { to: "/schedule", label: "Расписание", icon: Calendar, pipelineSteps: ["schedule"] },
    ],
  },
  {
    label: "Коммуникация",
    items: [
      { to: "/messaging", label: "Рассылки", icon: MessageSquare },
    ],
  },
  {
    label: "Аналитика",
    items: [
      { to: "/guests", label: "Аудитория бота", icon: UserCheck },
    ],
  },
  {
    label: "Администрирование",
    items: [
      { to: "/settings", label: "Настройки", icon: Settings },
      { to: "/audit-log", label: "Журнал", icon: ClipboardList },
    ],
  },
]

function deriveBadgeStatus(pipelineSteps: string[], allSteps: PipelineStep[]): BadgeStatus {
  const relevant = pipelineSteps
    .map((name) => allSteps.find((s) => s.name === name))
    .filter(Boolean)

  if (relevant.length === 0) return null

  const completed = relevant.filter((s) => s!.status === "completed").length
  if (completed === relevant.length) return "completed"
  if (completed > 0) return "attention"
  return "not_started"
}

function StatusBadge({ status }: { status: BadgeStatus }) {
  if (!status) return null

  const colorClass = {
    completed: "bg-green-500",
    attention: "bg-yellow-500",
    not_started: "bg-muted-foreground/30",
  }[status]

  return (
    <span
      className={cn("ml-auto w-2 h-2 rounded-full shrink-0", colorClass)}
      aria-label={status === "completed" ? "Завершено" : status === "attention" ? "Требует внимания" : "Не начато"}
    />
  )
}

interface SidebarProps {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const { data } = usePipelineStatus()

  const allSteps: PipelineStep[] = data?.phases.flatMap((p) => p.steps) ?? []

  return (
    <nav id="sidebar-nav" className="flex-1 py-4">
      <div className="space-y-6 px-2">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="px-3 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const badge = item.pipelineSteps
                  ? deriveBadgeStatus(item.pipelineSteps, allSteps)
                  : null

                return (
                  <li key={item.to + item.label}>
                    <NavLink
                      to={item.to}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                      <StatusBadge status={badge} />
                    </NavLink>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  )
}
