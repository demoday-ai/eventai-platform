import { useState, useCallback, useEffect } from "react"
import { MOCK_ORGANIZER_IDS } from "../lib/constants"

const AUTH_KEY = "demoday_auth"

interface AuthState {
  telegramId: string | null
  isAuthenticated: boolean
}

interface UseAuthReturn extends AuthState {
  login: (telegramId: string) => { success: boolean; error?: string }
  logout: () => void
}

function getStoredAuth(): AuthState {
  try {
    const stored = localStorage.getItem(AUTH_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        telegramId: parsed.telegramId,
        isAuthenticated: true,
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

  const login = useCallback((telegramId: string): { success: boolean; error?: string } => {
    const trimmedId = telegramId.trim()

    if (!trimmedId) {
      return { success: false, error: "Введите Telegram ID" }
    }

    // Check if ID is in allowed list (mock validation)
    if (!MOCK_ORGANIZER_IDS.includes(trimmedId)) {
      return { success: false, error: "Доступ запрещён. ID не в списке организаторов." }
    }

    // Store auth
    const authData = { telegramId: trimmedId }
    localStorage.setItem(AUTH_KEY, JSON.stringify(authData))

    setState({
      telegramId: trimmedId,
      isAuthenticated: true,
    })

    return { success: true }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_KEY)
    setState({ telegramId: null, isAuthenticated: false })
  }, [])

  return {
    ...state,
    login,
    logout,
  }
}
