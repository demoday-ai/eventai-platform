import { useState, useCallback, useEffect } from "react"
import { apiClient } from "../lib/api-client"

const AUTH_KEY = "demoday_auth"
const TOKEN_KEY = "auth_token"

interface AuthState {
  telegramId: string | null
  isAuthenticated: boolean
}

interface UseAuthReturn extends AuthState {
  login: (telegramId: string) => Promise<{ success: boolean; error?: string }>
  loginWithPassword: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
}

function getStoredAuth(): AuthState {
  try {
    const stored = localStorage.getItem(AUTH_KEY)
    const token = localStorage.getItem(TOKEN_KEY)
    if (stored && token) {
      const parsed = JSON.parse(stored)
      return {
        telegramId: parsed.telegramId,
        isAuthenticated: true,
      }
    }
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed.devBypass) {
        return {
          telegramId: parsed.telegramId,
          isAuthenticated: true,
        }
      }
    }
  } catch {
    // Invalid stored data
  }
  return { telegramId: null, isAuthenticated: false }
}

export function useAuth(): UseAuthReturn {
  const [state, setState] = useState<AuthState>(getStoredAuth)

  // Sync with localStorage on mount
  useEffect(() => {
    setState(getStoredAuth())
  }, [])

  const login = useCallback(async (telegramId: string): Promise<{ success: boolean; error?: string }> => {
    const trimmedId = telegramId.trim()

    if (!trimmedId) {
      return { success: false, error: "Введите Telegram ID" }
    }

    try {
      // Call dev-login API
      const { data } = await apiClient.post("/auth/dev-login", null, {
        params: { telegram_id: trimmedId },
      })

      // Store auth data and token
      localStorage.setItem(AUTH_KEY, JSON.stringify({ telegramId: trimmedId }))
      localStorage.setItem(TOKEN_KEY, data.access_token)

      setState({
        telegramId: trimmedId,
        isAuthenticated: true,
      })

      return { success: true }
    } catch (err) {
      console.error("Login error:", err)
      return { success: false, error: "Ошибка входа. Попробуйте позже." }
    }
  }, [])

  const loginWithPassword = useCallback(async (username: string, password: string) => {
    const trimmedUser = username.trim()
    const trimmedPass = password.trim()

    if (!trimmedUser || !trimmedPass) {
      return { success: false, error: "Введите логин и пароль" }
    }

    if (trimmedUser !== "admin" || trimmedPass !== "admin") {
      return { success: false, error: "Неверный логин или пароль" }
    }

    localStorage.setItem(AUTH_KEY, JSON.stringify({ telegramId: "admin", devBypass: true }))
    localStorage.removeItem(TOKEN_KEY)

    setState({
      telegramId: "admin",
      isAuthenticated: true,
    })

    return { success: true }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_KEY)
    localStorage.removeItem(TOKEN_KEY)
    setState({ telegramId: null, isAuthenticated: false })
  }, [])

  return {
    ...state,
    login,
    loginWithPassword,
    logout,
  }
}
