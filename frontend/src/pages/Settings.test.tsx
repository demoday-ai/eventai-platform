import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
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

vi.mock("../lib/api-client", () => ({
  getCurrentEvent: vi.fn(),
  updateCurrentEvent: vi.fn(),
  getAuditLog: vi.fn(),
  getOrganizers: vi.fn(),
  addOrganizer: vi.fn(),
  removeOrganizer: vi.fn(),
}))

const mockEvent: apiClient.Event = {
  id: "event-1",
  name: "Demo Day 2026",
  start_date: "2026-01-22",
  end_date: "2026-01-23",
  description: "Описание мероприятия",
}

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

const mockAuditLog: apiClient.AuditLogResponse = {
  total: 2,
  items: [
    {
      id: "a1",
      created_at: "2026-02-04T10:00:00Z",
      user_name: "Admin User",
      action: "upload_projects",
      entity_type: "projects",
      entity_id: null,
      details: { loaded: 10 },
    },
    {
      id: "a2",
      created_at: "2026-02-04T11:00:00Z",
      user_name: "Admin User",
      action: "event_update",
      entity_type: "event",
      entity_id: "evt-123",
      details: null,
    },
  ],
}

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

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getAuditLog).mockResolvedValue(mockAuditLog)
    vi.mocked(apiClient.getOrganizers).mockResolvedValue(mockOrganizers)
  })

  it("renders title and loading state", () => {
    vi.mocked(apiClient.getCurrentEvent).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText("Настройки")).toBeInTheDocument()
    expect(screen.getByText("Загрузка...")).toBeInTheDocument()
  })

  it("loads and displays current event data", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Мероприятие")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название") as HTMLInputElement
    expect(nameInput.value).toBe("Demo Day 2026")

    const startInput = screen.getByLabelText("Дата начала") as HTMLInputElement
    expect(startInput.value).toBe("2026-01-22")

    const endInput = screen.getByLabelText("Дата окончания") as HTMLInputElement
    expect(endInput.value).toBe("2026-01-23")

    const descInput = screen.getByLabelText("Описание") as HTMLTextAreaElement
    expect(descInput.value).toBe("Описание мероприятия")
  })

  it("calls updateCurrentEvent on save", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockResolvedValue({
      ...mockEvent,
      name: "New Name",
    })

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "New Name")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(apiClient.updateCurrentEvent).toHaveBeenCalledWith(
        expect.objectContaining({ name: "New Name" })
      )
    })
  })

  it("shows error on API load failure", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockRejectedValue(
      new Error("Network error")
    )

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/Ошибка загрузки/)).toBeInTheDocument()
    })
  })

  it("shows error on save failure", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockRejectedValue(
      new Error("Save failed")
    )

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Changed")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })

  it("validates end_date >= start_date", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Дата начала")).toBeInTheDocument()
    })

    const startInput = screen.getByLabelText("Дата начала")
    const endInput = screen.getByLabelText("Дата окончания")

    // Set end date before start date
    fireEvent.change(startInput, { target: { value: "2026-02-10" } })
    fireEvent.change(endInput, { target: { value: "2026-02-05" } })

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    expect(
      screen.getByText("Дата окончания должна быть не раньше даты начала")
    ).toBeInTheDocument()

    // updateCurrentEvent should NOT have been called
    expect(apiClient.updateCurrentEvent).not.toHaveBeenCalled()
  })

  it("shows success message after save", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Updated")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText("Сохранено")).toBeInTheDocument()
    })
  })

  it("renders audit log section", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Журнал действий")).toBeInTheDocument()
    })
  })

  it("loads and displays audit log entries", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getAuditLog).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getAllByText("Admin User").length).toBeGreaterThan(0)
    })
  })

  it("renders organizers section", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Организаторы")).toBeInTheDocument()
    })
  })

  it("loads and displays organizer list", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getOrganizers).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText("Админ Иванов")).toBeInTheDocument()
    })

    expect(screen.getByText("111222")).toBeInTheDocument()
    expect(screen.getByText("admin_user")).toBeInTheDocument()
    expect(screen.getByText("Петров Петр")).toBeInTheDocument()
  })

  it("shows add organizer form and submits", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
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
      expect(screen.getByLabelText("Telegram ID *")).toBeInTheDocument()
    })

    await userEvent.type(screen.getByLabelText("Telegram ID *"), "555666")
    await userEvent.type(screen.getByLabelText("Username"), "new_org")
    await userEvent.type(screen.getByLabelText("Имя"), "Новый Организатор")

    await userEvent.click(screen.getByRole("button", { name: "Добавить" }))

    await waitFor(() => {
      expect(apiClient.addOrganizer).toHaveBeenCalled()
    })

    expect(vi.mocked(apiClient.addOrganizer).mock.calls[0][0]).toEqual({
      telegram_id: "555666",
      telegram_username: "new_org",
      name: "Новый Организатор",
    })
  })
})
