import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../hooks/useAuth"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../components/ui/card"
import { APP_NAME } from "../lib/constants"

export function Login() {
  const [telegramId, setTelegramId] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    const result = await login(telegramId)

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
            <div className="space-y-2">
              <label htmlFor="telegram-id" className="text-sm font-medium">
                Telegram ID
              </label>
              <Input
                id="telegram-id"
                type="text"
                placeholder="Введите ваш Telegram ID"
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
                disabled={isLoading}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Числовой ID вашего Telegram аккаунта
              </p>
            </div>

            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                {error}
              </div>
            )}

            {/* Dev hint */}
            <div className="p-3 text-xs text-muted-foreground bg-muted rounded-md">
              <strong>Dev mode:</strong> Введите любой числовой Telegram ID
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
