import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { ExpertList } from "./ExpertList"
import * as apiClient from "../lib/api-client"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

vi.mock("../lib/api-client", () => ({
  getExperts: vi.fn(),
  createExpert: vi.fn(),
  updateExpert: vi.fn(),
}))

const mockExperts: apiClient.ExpertListItem[] = [
  {
    id: "e1",
    seed_id: "manual-abc123",
    name: "Иван Петров",
    telegram_username: "ivanp",
    position: "ML Engineer",
    tags: ["NLP", "CV"],
    bot_started: false,
    assignment_status: null,
  },
  {
    id: "e2",
    seed_id: "manual-def456",
    name: "Мария Сидорова",
    telegram_username: null,
    position: null,
    tags: [],
    bot_started: true,
    assignment_status: "confirmed",
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

describe("ExpertList", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders title and add button", () => {
    vi.mocked(apiClient.getExperts).mockImplementation(() => new Promise(() => {}))

    render(<ExpertList />, { wrapper: createWrapper() })

    expect(screen.getByText("Список экспертов")).toBeInTheDocument()
    expect(screen.getByText("Добавить эксперта")).toBeInTheDocument()
  })

  it("loads and displays expert table rows", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)

    render(<ExpertList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    expect(screen.getByText("@ivanp")).toBeInTheDocument()
    expect(screen.getByText("ML Engineer")).toBeInTheDocument()
    expect(screen.getByText("NLP")).toBeInTheDocument()
    expect(screen.getByText("CV")).toBeInTheDocument()
    expect(screen.getByText("Мария Сидорова")).toBeInTheDocument()
  })

  it("opens create dialog, fills form, and submits", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)
    vi.mocked(apiClient.createExpert).mockResolvedValue({
      id: "e3",
      seed_id: "manual-new",
      name: "Новый Эксперт",
      telegram_username: "newexpert",
      position: "Data Scientist",
      tags: ["ML"],
      bot_started: false,
      assignment_status: null,
    })

    render(<ExpertList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText("Добавить эксперта"))

    expect(screen.getByText("Добавить эксперта", { selector: "[class*=CardTitle] *,h3" })).toBeInTheDocument()

    const nameInput = screen.getByLabelText("Имя")
    await userEvent.type(nameInput, "Новый Эксперт")

    const telegramInput = screen.getByLabelText("Telegram")
    await userEvent.type(telegramInput, "@newexpert")

    const positionInput = screen.getByLabelText("Должность")
    await userEvent.type(positionInput, "Data Scientist")

    const tagsInput = screen.getByLabelText("Теги (через запятую)")
    await userEvent.type(tagsInput, "ML")

    await userEvent.click(screen.getByText("Сохранить"))

    await waitFor(() => {
      expect(apiClient.createExpert).toHaveBeenCalledWith({
        name: "Новый Эксперт",
        telegram_username: "@newexpert",
        position: "Data Scientist",
        tags: ["ML"],
      })
    })
  })

  it("opens edit dialog with pre-filled data", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)

    render(<ExpertList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText("Редактировать")
    await userEvent.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByTestId("expert-dialog")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Имя") as HTMLInputElement
    expect(nameInput.value).toBe("Иван Петров")

    const telegramInput = screen.getByLabelText("Telegram") as HTMLInputElement
    expect(telegramInput.value).toBe("ivanp")

    const positionInput = screen.getByLabelText("Должность") as HTMLInputElement
    expect(positionInput.value).toBe("ML Engineer")

    const tagsInput = screen.getByLabelText("Теги (через запятую)") as HTMLInputElement
    expect(tagsInput.value).toBe("NLP, CV")
  })

  it("shows error on API failure", async () => {
    vi.mocked(apiClient.getExperts).mockRejectedValue(new Error("Network error"))

    render(<ExpertList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Ошибка загрузки списка экспертов")).toBeInTheDocument()
    })
  })

  it("validates that name is required on create", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue([])

    render(<ExpertList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Добавить эксперта")).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText("Добавить эксперта"))

    await waitFor(() => {
      expect(screen.getByTestId("expert-dialog")).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText("Сохранить"))

    expect(screen.getByText("Имя обязательно")).toBeInTheDocument()
    expect(apiClient.createExpert).not.toHaveBeenCalled()
  })
})
