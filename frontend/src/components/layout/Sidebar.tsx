import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Upload,
  Layers,
  Users,
  Calendar,
  FolderOpen,
} from "lucide-react"
import { cn } from "../../lib/utils"

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/import", label: "Импорт данных", icon: Upload },
  { to: "/clustering", label: "Кластеризация", icon: Layers },
  { to: "/experts", label: "Эксперты", icon: Users },
  { to: "/schedule", label: "Расписание", icon: Calendar },
  { to: "/projects", label: "Проекты", icon: FolderOpen },
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
