import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Settings } from "./Settings"
import * as apiClient from "../lib/api-client"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

vi.mock("../lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api-client")>()
  return {
    ...actual,
    getOrganizers: vi.fn(),
    addOrganizer: vi.fn(),
    removeOrganizer: vi.fn(),
  }
})

const mockOrganizers: apiClient.OrganizerItem[] = [
  {
    id: "org-1",
    telegram_id: "111222",
    telegram_username: "admin_user",
    name: "Админ Иванов",
    added_by: "env",
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: "org-2",
    telegram_id: "333444",
    telegram_username: null,
    name: "Петров Петр",
    added_by: "Админ Иванов",
    created_at: "2026-01-20T12:00:00Z",
  },
]

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getOrganizers).mockResolvedValue(mockOrganizers)
  })

  it("renders title and organizers section", async () => {
    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText("Настройки")).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText("Организаторы")).toBeInTheDocument()
    })
  })

  it("loads and displays organizer list", async () => {
    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getOrganizers).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText("Админ Иванов")).toBeInTheDocument()
    })

    expect(screen.getByText("admin_user")).toBeInTheDocument()
    expect(screen.getByText("Петров Петр")).toBeInTheDocument()
  })

  it("shows add organizer form and submits", async () => {
    vi.mocked(apiClient.addOrganizer).mockResolvedValue({
      id: "org-3",
      telegram_id: "555666",
      telegram_username: "new_org",
      name: "Новый Организатор",
      added_by: null,
      created_at: "2026-02-04T15:00:00Z",
    })

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Добавить организатора")).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText("Добавить организатора"))

    await waitFor(() => {
      expect(screen.getByLabelText("Username *")).toBeInTheDocument()
    })

    await userEvent.type(screen.getByLabelText("Username *"), "new_org")
    await userEvent.type(screen.getByLabelText("Имя"), "Новый Организатор")

    const submitButtons = screen.getAllByRole("button", { name: "Добавить" })
    await userEvent.click(submitButtons[submitButtons.length - 1])

    await waitFor(() => {
      expect(apiClient.addOrganizer).toHaveBeenCalled()
    })

    expect(vi.mocked(apiClient.addOrganizer).mock.calls[0][0]).toEqual({
      telegram_id: "",
      telegram_username: "new_org",
      name: "Новый Организатор",
    })
  })

  it("does not show event or tags sections", () => {
    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.queryByText("Мероприятие")).not.toBeInTheDocument()
    expect(screen.queryByText("Теги конференции")).not.toBeInTheDocument()
  })
})
