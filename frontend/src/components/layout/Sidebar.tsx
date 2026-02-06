import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Upload,
  Layers,
  Users,
  UserCheck,
  Calendar,
  FolderOpen,
  ShieldCheck,
  MessageSquare,
  Settings,
} from "lucide-react"
import { cn } from "../../lib/utils"

const navGroups = [
  {
    label: "Подготовка",
    items: [
      { to: "/settings", label: "Настройки", icon: Settings },
      { to: "/import", label: "Импорт данных", icon: Upload },
      { to: "/projects", label: "Проекты", icon: FolderOpen },
    ],
  },
  {
    label: "Распределение",
    items: [
      { to: "/clustering", label: "Кластеризация", icon: Layers },
      { to: "/experts", label: "Эксперты", icon: Users },
      { to: "/schedule", label: "Расписание", icon: Calendar },
    ],
  },
  {
    label: "Коммуникация",
    items: [
      { to: "/messaging", label: "Рассылки", icon: MessageSquare },
    ],
  },
  {
    label: "Мониторинг",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/coverage", label: "Покрытие", icon: ShieldCheck },
      { to: "/guests", label: "Гости", icon: UserCheck },
    ],
  },
]

interface SidebarProps {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <nav className="flex-1 py-4">
      <div className="space-y-6 px-2">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="px-3 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
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
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  )
}
