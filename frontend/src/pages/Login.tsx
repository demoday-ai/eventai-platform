import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../hooks/useAuth"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../components/ui/card"
import { APP_NAME } from "../lib/constants"

export function Login() {
  const [adminUser, setAdminUser] = useState("")
  const [adminPassword, setAdminPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { loginWithPassword } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    const result = await loginWithPassword(adminUser, adminPassword)

    if (result.success) {
      navigate("/dashboard")
    } else {
      setError(result.error || "Ошибка входа")
    }

    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{APP_NAME}</CardTitle>
          <CardDescription>
            Войдите для доступа к панели управления
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="rounded-md border border-muted p-3 space-y-3">
              <p className="text-sm font-medium">Админ-вход</p>
              <div className="grid gap-2">
                <label htmlFor="admin-user" className="text-xs text-muted-foreground">
                  Логин
                </label>
                <Input
                  id="admin-user"
                  type="text"
                  placeholder="Введите логин"
                  value={adminUser}
                  onChange={(e) => setAdminUser(e.target.value)}
                  disabled={isLoading}
                  autoFocus
                />
              </div>
              <div className="grid gap-2">
                <label htmlFor="admin-password" className="text-xs text-muted-foreground">
                  Пароль
                </label>
                <Input
                  id="admin-password"
                  type="password"
                  placeholder="Введите пароль"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                {error}
              </div>
            )}

            {/* Dev hint */}
            <div className="p-3 text-xs text-muted-foreground bg-muted rounded-md">
              <strong>Dev mode:</strong> логин/пароль для тестовой среды.
            </div>
          </CardContent>

          <CardFooter>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Проверка..." : "Войти"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
