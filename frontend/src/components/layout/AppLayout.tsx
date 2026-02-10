import { useState, useEffect } from "react"
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { useAuth } from "../../hooks/useAuth"
import { Button } from "../ui/button"
import { APP_NAME } from "../../lib/constants"
import { Sidebar } from "./Sidebar"
import { GlobalStepper } from "../dashboard/GlobalStepper"

export function AppLayout() {
  const { telegramId, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Close sidebar on resize to desktop
  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)")
    const handleChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        setSidebarOpen(false)
      }
    }
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [])

  return (
    <div className="min-h-screen bg-muted/30 flex flex-col">
      <header className="border-b bg-background sticky top-0 z-40">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Открыть меню"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-xl font-semibold">{APP_NAME}</h1>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              ID: {telegramId}
            </span>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Выйти
            </Button>
          </div>
        </div>
      </header>

      <GlobalStepper />

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex w-56 border-r bg-background flex-col">
          <Sidebar onNavigate={() => {}} />
        </aside>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setSidebarOpen(false)}
            />
            {/* Sidebar panel */}
            <aside className="absolute inset-y-0 left-0 w-64 bg-background shadow-xl animate-slide-in-left">
              <div className="flex items-center justify-between p-4 border-b">
                <span className="font-semibold">{APP_NAME}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(false)}
                  aria-label="Закрыть меню"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <Sidebar onNavigate={() => setSidebarOpen(false)} />
            </aside>
          </div>
        )}

        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      <footer className="border-t bg-background py-4 px-6 text-sm text-muted-foreground">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-center md:text-left">
            <p className="font-medium">Разработано на интенсиве AI Talent Camp 2026</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-6 text-xs">
            <span><strong>Дмитрий Горбунов</strong> (@grbn_dima) — Продукт, Backend, UX/UI, Frontend</span>
            <span><strong>Иван Александров</strong> (@ivanich_spb) — Backend, DevOps</span>
            <span><strong>Анастасия Гапеева</strong> (@agapeeva) — UX/UI, Оценка качества</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
