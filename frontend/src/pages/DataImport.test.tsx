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

vi.mock("../lib/api-client", () => ({
  uploadProjects: (...args: unknown[]) => mockUploadProjects(...args),
  uploadExperts: (...args: unknown[]) => mockUploadExperts(...args),
  uploadGuests: (...args: unknown[]) => mockUploadGuests(...args),
  getDashboard: () => mockGetDashboard(),
  getProjects: () => mockGetProjects(),
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
    // Default: empty data
    mockGetDashboard.mockResolvedValue({
      students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
      experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
      guests: { total: 0, by_subtype: [] },
      rooms: { total: 0, with_experts: 0, without_experts: 0 },
      alerts: [],
    })
    mockGetProjects.mockResolvedValue([])
  })

  it("renders all upload sections", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    expect(screen.getByText("Импорт данных")).toBeInTheDocument()
    expect(screen.getByText("Проекты")).toBeInTheDocument()
    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Гости")).toBeInTheDocument()
  })

  it("disables upload button when no file selected", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    const buttons = screen.getAllByText("Загрузить")
    expect(buttons[0]).toBeDisabled()
    expect(buttons[1]).toBeDisabled()
  })

  it("handles successful project upload", async () => {
    const user = userEvent.setup()
    mockUploadProjects.mockResolvedValue({
      loaded: 10,
      errors: 0,
      duplicates: 0,
      error_details: [],
      duplicate_titles: [],
    })

    render(<DataImport />, { wrapper: createWrapper() })

    const file = new File(["test"], "projects.csv", { type: "text/csv" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    const uploadBtn = screen.getAllByText("Загрузить")[0]
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(screen.getByText("Результат импорта проектов")).toBeInTheDocument()
      expect(screen.getByText("10")).toBeInTheDocument()
    })
  })

  it("handles project upload 409 conflict", async () => {
    const user = userEvent.setup()
    const error = new AxiosError("Conflict", "409", undefined, undefined, {
      status: 409,
      statusText: "Conflict",
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: {
        message: "Заменить предыдущие данные (5 проектов) новыми (10 проектов)?",
        existing_count: 5,
        new_count: 10,
      },
    })
    mockUploadProjects.mockRejectedValue(error)

    render(<DataImport />, { wrapper: createWrapper() })

    const file = new File(["test"], "projects.csv", { type: "text/csv" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[0] as HTMLInputElement, file)

    const uploadBtn = screen.getAllByText("Загрузить")[0]
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

    const file = new File(["[]"], "experts.json", { type: "application/json" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[1] as HTMLInputElement, file)

    const uploadBtn = screen.getAllByText("Загрузить")[1]
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(screen.getByText("Результат импорта экспертов")).toBeInTheDocument()
      expect(screen.getByText("18")).toBeInTheDocument()
    })
  })

  it("renders Гости section with subtype dropdown", () => {
    render(<DataImport />, { wrapper: createWrapper() })

    expect(screen.getByText("Гости")).toBeInTheDocument()
    expect(screen.getByLabelText("Тип гостя")).toBeInTheDocument()
  })

  it("handles successful guest upload", async () => {
    const user = userEvent.setup()
    mockUploadGuests.mockResolvedValue({
      total_parsed: 5,
      imported: 4,
      duplicates: 1,
      errors: [],
    })

    render(<DataImport />, { wrapper: createWrapper() })

    // Select subtype
    const subtypeSelect = screen.getByLabelText("Тип гостя")
    await user.selectOptions(subtypeSelect, "investor")

    // Upload file
    const file = new File(["[]"], "guests.json", { type: "application/json" })
    const inputs = document.querySelectorAll('input[type="file"]')
    await user.upload(inputs[2] as HTMLInputElement, file)

    const uploadBtn = screen.getAllByText("Загрузить")[2]
    await user.click(uploadBtn)

    await waitFor(() => {
      expect(screen.getByText("Результат импорта гостей")).toBeInTheDocument()
      expect(screen.getByText("4")).toBeInTheDocument()
    })
  })
})
