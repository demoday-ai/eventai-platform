import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { ExpertListTab } from "./ExpertList"
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
  updateExpertStatus: vi.fn(),
  deleteExpert: vi.fn(),
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

describe("ExpertListTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders add button", () => {
    vi.mocked(apiClient.getExperts).mockImplementation(() => new Promise(() => {}))

    render(<ExpertListTab />, { wrapper: createWrapper() })

    expect(screen.getByText("Добавить эксперта")).toBeInTheDocument()
  })

  it("loads and displays expert table rows", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)

    render(<ExpertListTab />, { wrapper: createWrapper() })

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

    render(<ExpertListTab />, { wrapper: createWrapper() })

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

    render(<ExpertListTab />, { wrapper: createWrapper() })

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

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Ошибка загрузки списка экспертов")).toBeInTheDocument()
    })
  })

  it("validates that name is required on create", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue([])

    render(<ExpertListTab />, { wrapper: createWrapper() })

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

  it("displays status badges for experts", async () => {
    const expertsWithStatuses: apiClient.ExpertListItem[] = [
      { ...mockExperts[0], assignment_status: "invited" },
      { ...mockExperts[1], assignment_status: "confirmed" },
    ]
    vi.mocked(apiClient.getExperts).mockResolvedValue(expertsWithStatuses)

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    expect(screen.getByText("Приглашён")).toBeInTheDocument()
    expect(screen.getByText("Подтверждён")).toBeInTheDocument()
  })

  it("shows confirm/decline buttons for invited expert and calls API on confirm", async () => {
    const expertsWithInvited: apiClient.ExpertListItem[] = [
      { ...mockExperts[0], assignment_status: "invited" },
    ]
    vi.mocked(apiClient.getExperts).mockResolvedValue(expertsWithInvited)
    vi.mocked(apiClient.updateExpertStatus).mockResolvedValue({
      ...mockExperts[0],
      assignment_status: "confirmed",
    })

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    expect(screen.getByText("Подтвердить")).toBeInTheDocument()
    expect(screen.getByText("Отклонить")).toBeInTheDocument()

    await userEvent.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(apiClient.updateExpertStatus).toHaveBeenCalledWith("e1", "confirmed")
    })
  })

  it("does not show confirm/decline buttons for confirmed expert", async () => {
    const confirmedExperts: apiClient.ExpertListItem[] = [
      { ...mockExperts[1], assignment_status: "confirmed" },
    ]
    vi.mocked(apiClient.getExperts).mockResolvedValue(confirmedExperts)

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Мария Сидорова")).toBeInTheDocument()
    })

    expect(screen.getByText("Подтверждён")).toBeInTheDocument()
    expect(screen.queryByText("Подтвердить")).not.toBeInTheDocument()
    expect(screen.queryByText("Отклонить")).not.toBeInTheDocument()
  })
  it("deletes an expert after confirmation", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)
    vi.mocked(apiClient.deleteExpert).mockResolvedValue({ deleted: "e1" })
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText("Удалить")
    await userEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(apiClient.deleteExpert).toHaveBeenCalledWith("e1")
    })
    confirmSpy.mockRestore()
  })

  it("does not delete when confirmation is cancelled", async () => {
    vi.mocked(apiClient.getExperts).mockResolvedValue(mockExperts)
    vi.mocked(apiClient.deleteExpert).mockResolvedValue({ deleted: "e1" })
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false)

    render(<ExpertListTab />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Петров")).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText("Удалить")[0])

    expect(apiClient.deleteExpert).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })
})
