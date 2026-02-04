import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Upload,
  Layers,
  Users,
  Calendar,
  FolderOpen,
  ShieldCheck,
  UserCheck,
  Bell,
  MessageSquare,
  Settings,
  FileText,
} from "lucide-react"
import { cn } from "../../lib/utils"

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/import", label: "Импорт данных", icon: Upload },
  { to: "/clustering", label: "Кластеризация", icon: Layers },
  { to: "/experts", label: "Эксперты", icon: Users },
  { to: "/briefing", label: "Брифинг", icon: FileText },
  { to: "/coverage", label: "Покрытие", icon: ShieldCheck },
  { to: "/schedule", label: "Расписание", icon: Calendar },
  { to: "/participation", label: "Участие", icon: UserCheck },
  { to: "/notifications", label: "Уведомления", icon: Bell },
  { to: "/messaging", label: "Рассылка", icon: MessageSquare },
  { to: "/projects", label: "Проекты", icon: FolderOpen },
  { to: "/settings", label: "Настройки", icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="w-56 border-r bg-background flex flex-col">
      <nav className="flex-1 py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
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
      </nav>
    </aside>
  )
}
