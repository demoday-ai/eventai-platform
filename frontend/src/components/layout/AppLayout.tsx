import { Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "../../hooks/useAuth"
import { Button } from "../ui/button"
import { APP_NAME } from "../../lib/constants"
import { Sidebar } from "./Sidebar"

export function AppLayout() {
  const { telegramId, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  return (
    <div className="min-h-screen bg-muted/30 flex flex-col">
      <header className="border-b bg-background">
        <div className="px-4 py-3 flex items-center justify-between">
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
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
