import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { DataImport } from "./DataImport"
import { AxiosError, AxiosHeaders } from "axios"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockUploadProjects = vi.fn()
const mockUploadExperts = vi.fn()
const mockUploadGuests = vi.fn()
const mockGetDashboard = vi.fn()
const mockGetProjects = vi.fn()
const mockGetUploadJobStatus = vi.fn()
const mockGetCurrentEvent = vi.fn()
const mockCreateEvent = vi.fn()
const mockUpdateCurrentEvent = vi.fn()

vi.mock("../lib/api-client", () => ({
  uploadProjects: (...args: unknown[]) => mockUploadProjects(...args),
  uploadExperts: (...args: unknown[]) => mockUploadExperts(...args),
  uploadGuests: (...args: unknown[]) => mockUploadGuests(...args),
  getDashboard: () => mockGetDashboard(),
  getProjects: () => mockGetProjects(),
  getUploadJobStatus: (...args: unknown[]) => mockGetUploadJobStatus(...args),
  getCurrentEvent: () => mockGetCurrentEvent(),
  createEvent: (...args: unknown[]) => mockCreateEvent(...args),
  updateCurrentEvent: (...args: unknown[]) => mockUpdateCurrentEvent(...args),
  isNoEventError: (error: unknown) => {
    if (error && typeof error === "object" && "response" in error) {
      const resp = (error as { response?: { status?: number } }).response
      return resp?.status === 404
    }
    return false
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("DataImport", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDashboard.mockResolvedValue({
      students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
      experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
      guests: { total: 0, by_subtype: [] },
      rooms: { total: 0, with_experts: 0, without_experts: 0 },
      alerts: [],
    })
    mockGetProjects.mockResolvedValue([])
    mockGetCurrentEvent.mockResolvedValue({
      id: "test-event-id",
      name: "Demo Day 2026",
      start_date: "2026-03-15",
      end_date: "2026-03-16",
      description: null,
    })
  })

  it("renders 4 numbered tabs", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    expect(screen.getByText("Импорт данных")).toBeInTheDocument()
    expect(screen.getByText("1. Событие")).toBeInTheDocument()
    expect(screen.getByText("2. Проекты")).toBeInTheDocument()
    expect(screen.getByText("3. Эксперты")).toBeInTheDocument()
    expect(screen.getByText("4. Гости")).toBeInTheDocument()
  })

  it("shows event tab as active by default", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    const eventTab = screen.getByText("1. Событие")
    expect(eventTab).toHaveAttribute("data-state", "active")
  })

  it("switches between tabs", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    const projectsTab = screen.getByText("2. Проекты")
    await user.click(projectsTab)
    expect(projectsTab).toHaveAttribute("data-state", "active")

    const eventTab = screen.getByText("1. Событие")
    expect(eventTab).toHaveAttribute("data-state", "inactive")
  })

  it("shows event creation form when no event exists", async () => {
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создание мероприятия")).toBeInTheDocument()
    })
    expect(screen.getByLabelText("Название")).toBeInTheDocument()
    expect(screen.getByLabelText("Дата начала")).toBeInTheDocument()
    expect(screen.getByLabelText("Дата окончания")).toBeInTheDocument()
    expect(screen.getByText("Создать")).toBeInTheDocument()
  })

  it("shows event edit form when event exists", async () => {
    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Редактирование мероприятия")).toBeInTheDocument()
    })
    expect(screen.getByText("Сохранить")).toBeInTheDocument()
  })

  it("shows no-event hint on projects tab when no event", async () => {
    const user = userEvent.setup()
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByText("2. Проекты"))

    await waitFor(() => {
      expect(screen.getByText(/Сначала создайте мероприятие/)).toBeInTheDocument()
    })
  })

  it("shows no-event hint on experts tab when no event", async () => {
    const user = userEvent.setup()
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByText("3. Эксперты"))

    await waitFor(() => {
      expect(screen.getByText(/Сначала создайте мероприятие/)).toBeInTheDocument()
    })
  })

  it("shows upload sections on projects tab when event exists", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByText("2. Проекты"))

    await waitFor(() => {
      expect(screen.getByText("Проекты")).toBeInTheDocument()
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })
  })

  it("handles successful project upload", async () => {
    const user = userEvent.setup()

    mockUploadProjects.mockResolvedValue({
      job_id: "test-job-123",
      status: "pending",
      total: 10,
    })
    mockGetUploadJobStatus.mockResolvedValue({
      job_id: "test-job-123",
      status: "completed",
      result: {
        loaded: 10,
        tags_generated: 5,
        errors: 0,
        duplicates: 0,
        error_details: [],
        duplicate_titles: [],
      },
    })

    render(<DataImport />, { wrapper: createWrapper() })

    // Switch to projects tab
    await user.click(screen.getByText("2. Проекты"))

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })

    const file = new File(["test"], "projects.csv", { type: "text/csv" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    const uploadBtn = screen.getByText("Загрузить")
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(screen.getByText("Результат импорта проектов")).toBeInTheDocument()
      expect(screen.getByText("10")).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it("handles project upload 409 conflict", async () => {
    const user = userEvent.setup()
    const error = new AxiosError("Conflict", "409", undefined, undefined, {
      status: 409,
      statusText: "Conflict",
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: {
        detail: {
          message: "Заменить предыдущие данные (5 проектов) новыми (10 проектов)?",
          existing_count: 5,
          new_count: 10,
        },
      },
    })
    mockUploadProjects.mockRejectedValue(error)

    render(<DataImport />, { wrapper: createWrapper() })

    // Switch to projects tab
    await user.click(screen.getByText("2. Проекты"))

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })

    const file = new File(["test"], "projects.csv", { type: "text/csv" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    const uploadBtn = screen.getByText("Загрузить")
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(
        screen.getByText("Заменить предыдущие данные (5 проектов) новыми (10 проектов)?")
      ).toBeInTheDocument()
      expect(screen.getByText("Заменить")).toBeInTheDocument()
    })
  })

  it("handles successful expert upload", async () => {
    const user = userEvent.setup()
    mockUploadExperts.mockResolvedValue({
      total_parsed: 20,
      imported: 18,
      with_tags: 15,
      without_tags: 3,
      errors: [],
    })

    render(<DataImport />, { wrapper: createWrapper() })

    // Switch to experts tab
    await user.click(screen.getByText("3. Эксперты"))

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })

    const file = new File(["[]"], "experts.json", { type: "application/json" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    const uploadBtn = screen.getByText("Загрузить")
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(screen.getByText("Результат импорта экспертов")).toBeInTheDocument()
      expect(screen.getByText("18")).toBeInTheDocument()
    })
  })

  it("renders Гости tab with subtype dropdown", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByText("4. Гости"))

    await waitFor(() => {
      expect(screen.getByLabelText("Тип гостя")).toBeInTheDocument()
    })
  })

  it("validates event creation with empty name", async () => {
    const user = userEvent.setup()
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создать")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Создать"))

    expect(screen.getByText("Введите название мероприятия")).toBeInTheDocument()
  })

  it("navigates to event tab from no-event hint", async () => {
    const user = userEvent.setup()
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<DataImport />, { wrapper: createWrapper() })

    // Go to projects tab
    await user.click(screen.getByText("2. Проекты"))

    await waitFor(() => {
      expect(screen.getByText(/Сначала создайте мероприятие/)).toBeInTheDocument()
    })

    // Click the link to go to event tab
    await user.click(screen.getByText("Перейти к созданию мероприятия"))

    // Should now show event tab
    expect(screen.getByText("1. Событие")).toHaveAttribute("data-state", "active")
  })
})
