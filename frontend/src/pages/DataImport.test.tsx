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
const mockPreviewProjectUpload = vi.fn()
const mockPreviewExpertUpload = vi.fn()
const mockPreviewGuestUpload = vi.fn()
const mockMergeProjects = vi.fn()
const mockMergeExperts = vi.fn()
const mockMergeGuests = vi.fn()
const mockDeleteAllProjects = vi.fn()
const mockDeleteAllExperts = vi.fn()
const mockDeleteAllGuests = vi.fn()

vi.mock("../lib/api-client", () => ({
  uploadProjects: (...args: unknown[]) => mockUploadProjects(...args),
  uploadExperts: (...args: unknown[]) => mockUploadExperts(...args),
  uploadGuests: (...args: unknown[]) => mockUploadGuests(...args),
  getDashboard: () => mockGetDashboard(),
  getProjects: () => mockGetProjects(),
  getUploadJobStatus: (...args: unknown[]) => mockGetUploadJobStatus(...args),
  getCurrentEvent: () => mockGetCurrentEvent(),
  previewProjectUpload: (...args: unknown[]) => mockPreviewProjectUpload(...args),
  previewExpertUpload: (...args: unknown[]) => mockPreviewExpertUpload(...args),
  previewGuestUpload: (...args: unknown[]) => mockPreviewGuestUpload(...args),
  mergeProjects: (...args: unknown[]) => mockMergeProjects(...args),
  mergeExperts: (...args: unknown[]) => mockMergeExperts(...args),
  mergeGuests: (...args: unknown[]) => mockMergeGuests(...args),
  deleteAllProjects: (...args: unknown[]) => mockDeleteAllProjects(...args),
  deleteAllExperts: (...args: unknown[]) => mockDeleteAllExperts(...args),
  deleteAllGuests: (...args: unknown[]) => mockDeleteAllGuests(...args),
  isNoEventError: (error: unknown) => {
    if (error && typeof error === "object" && "response" in error) {
      const resp = (error as { response?: { status?: number } }).response
      return resp?.status === 404
    }
    return false
  },
}))

const EMPTY_DASHBOARD = {
  students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
  experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
  guests: { total: 0, by_subtype: [] },
  rooms: { total: 0, with_experts: 0, without_experts: 0 },
  projects: { total: 0 },
  partners: { total: 0, from_bot: 0, from_import: 0 },
  alerts: [],
}

const DASHBOARD_WITH_DATA = {
  ...EMPTY_DASHBOARD,
  projects: { total: 10 },
  experts: { total: 5, confirmed: 3, pending: 1, invited: 1 },
  guests: { total: 20, by_subtype: [{ subtype: "student", count: 15 }, { subtype: "business_partner", count: 5 }] },
  partners: { total: 5, from_bot: 0, from_import: 5 },
}

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
    mockGetDashboard.mockResolvedValue(EMPTY_DASHBOARD)
    mockGetProjects.mockResolvedValue([])
    mockGetCurrentEvent.mockResolvedValue({
      id: "test-event-id",
      name: "Demo Day 2026",
      start_date: "2026-03-15",
      end_date: "2026-03-16",
      description: null,
    })
  })

  it("renders 4 tabs", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    expect(screen.getByText("Импорт данных")).toBeInTheDocument()
    expect(screen.getByText("Проекты")).toBeInTheDocument()
    expect(screen.getByText("Студенты")).toBeInTheDocument()
    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Партнёры")).toBeInTheDocument()
  })

  it("shows projects tab as active by default", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    const projectsTab = screen.getByRole("tab", { name: "Проекты" })
    expect(projectsTab).toHaveAttribute("data-state", "active")
  })

  it("switches between tabs", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    const expertsTab = screen.getByRole("tab", { name: "Эксперты" })
    await user.click(expertsTab)
    expect(expertsTab).toHaveAttribute("data-state", "active")

    const projectsTab = screen.getByRole("tab", { name: "Проекты" })
    expect(projectsTab).toHaveAttribute("data-state", "inactive")
  })

  it("shows no-event hint on projects tab when no event", async () => {
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

    await user.click(screen.getByRole("tab", { name: "Эксперты" }))

    await waitFor(() => {
      expect(screen.getByText(/Сначала создайте мероприятие/)).toBeInTheDocument()
    })
  })

  it("shows upload button when DB is empty", async () => {
    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })
  })

  it("shows analyze button when DB has data", async () => {
    mockGetDashboard.mockResolvedValue(DASHBOARD_WITH_DATA)

    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Анализировать")).toBeInTheDocument()
    })
  })

  it("handles project preview and shows merge preview card", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(DASHBOARD_WITH_DATA)

    mockPreviewProjectUpload.mockResolvedValue({
      new_count: 5,
      duplicate_count: 3,
      updated_count: 2,
      error_count: 0,
      new_items: [{ name: "Проект 1", telegram: null }],
      updated_items: [],
      errors: [],
      with_tags_in_db: 10,
      missing_tags_in_db: 2,
    })

    render(<DataImport />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Анализировать")).toBeInTheDocument()
    })

    const file = new File(["test"], "projects.csv", { type: "text/csv" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    await user.click(screen.getByText("Анализировать"))

    await waitFor(() => {
      expect(screen.getByText("Результат анализа файла")).toBeInTheDocument()
      expect(screen.getByText("5")).toBeInTheDocument() // new_count
    })
  })

  it("handles expert preview", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(DASHBOARD_WITH_DATA)

    mockPreviewExpertUpload.mockResolvedValue({
      new_count: 10,
      duplicate_count: 5,
      updated_count: 3,
      error_count: 0,
      new_items: [],
      updated_items: [],
      errors: [],
      with_tags_in_db: null,
      missing_tags_in_db: null,
    })

    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("tab", { name: "Эксперты" }))

    await waitFor(() => {
      expect(screen.getByText("Анализировать")).toBeInTheDocument()
    })

    const file = new File(["[]"], "experts.json", { type: "application/json" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    await user.click(screen.getByText("Анализировать"))

    await waitFor(() => {
      expect(screen.getByText("Результат анализа файла")).toBeInTheDocument()
    })
  })

  it("renders Students tab with upload button when empty", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("tab", { name: "Студенты" }))

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })
  })

  it("renders Partners tab with upload button when empty", async () => {
    const user = userEvent.setup()
    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("tab", { name: "Партнёры" }))

    await waitFor(() => {
      expect(screen.getByText("Загрузить")).toBeInTheDocument()
    })
  })

  it("calls previewGuestUpload for students when data exists", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(DASHBOARD_WITH_DATA)

    mockPreviewGuestUpload.mockResolvedValue({
      new_count: 5,
      duplicate_count: 0,
      updated_count: 0,
      error_count: 0,
      new_items: [],
      updated_items: [],
      errors: [],
      with_tags_in_db: null,
      missing_tags_in_db: null,
    })

    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("tab", { name: "Студенты" }))

    await waitFor(() => {
      expect(screen.getByText("Анализировать")).toBeInTheDocument()
    })

    const file = new File(["test"], "students.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    await user.click(screen.getByText("Анализировать"))

    await waitFor(() => {
      expect(mockPreviewGuestUpload).toHaveBeenCalledWith(file, "student")
    })
  })

  it("calls previewGuestUpload for partners when data exists", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(DASHBOARD_WITH_DATA)

    mockPreviewGuestUpload.mockResolvedValue({
      new_count: 3,
      duplicate_count: 0,
      updated_count: 0,
      error_count: 0,
      new_items: [],
      updated_items: [],
      errors: [],
      with_tags_in_db: null,
      missing_tags_in_db: null,
    })

    render(<DataImport />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("tab", { name: "Партнёры" }))

    await waitFor(() => {
      expect(screen.getByText("Анализировать")).toBeInTheDocument()
    })

    const file = new File(["test"], "partners.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    await user.click(screen.getByText("Анализировать"))

    await waitFor(() => {
      expect(mockPreviewGuestUpload).toHaveBeenCalledWith(file, "business_partner")
    })
  })

  it("shows link to event page from no-event hint", async () => {
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
      expect(screen.getByText(/Сначала создайте мероприятие/)).toBeInTheDocument()
    })

    const link = screen.getByText("Перейти к созданию мероприятия").closest("a")
    expect(link).toHaveAttribute("href", "/event")
  })
})
