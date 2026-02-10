import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Event } from "./Event"
import { AxiosError, AxiosHeaders } from "axios"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetCurrentEvent = vi.fn()
const mockCreateEvent = vi.fn()
const mockUpdateCurrentEvent = vi.fn()

vi.mock("../lib/api-client", () => ({
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

describe("Event", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page title", () => {
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<Event />, { wrapper: createWrapper() })

    expect(screen.getByText("Мероприятие")).toBeInTheDocument()
  })

  it("shows creation form when no event exists", async () => {
    mockGetCurrentEvent.mockRejectedValue(
      new AxiosError("Not found", "404", undefined, undefined, {
        status: 404,
        statusText: "Not Found",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "No active event" },
      })
    )

    render(<Event />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создание мероприятия")).toBeInTheDocument()
    })
    expect(screen.getByLabelText("Название")).toBeInTheDocument()
    expect(screen.getByLabelText("Дата начала")).toBeInTheDocument()
    expect(screen.getByLabelText("Дата окончания")).toBeInTheDocument()
    expect(screen.getByText("Создать")).toBeInTheDocument()
  })

  it("shows edit form when event exists", async () => {
    mockGetCurrentEvent.mockResolvedValue({
      id: "test-event-id",
      name: "Demo Day 2026",
      start_date: "2026-03-15",
      end_date: "2026-03-16",
      description: "Test description",
    })

    render(<Event />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Редактирование мероприятия")).toBeInTheDocument()
    })
    expect(screen.getByText("Сохранить")).toBeInTheDocument()
  })

  it("validates empty name on create", async () => {
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

    render(<Event />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создать")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Создать"))

    expect(screen.getByText("Введите название мероприятия")).toBeInTheDocument()
  })

  it("calls createEvent on submit", async () => {
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
    mockCreateEvent.mockResolvedValue({
      id: "new-event",
      name: "Test Event",
      start_date: "2026-04-01",
      end_date: "2026-04-02",
      description: null,
    })

    render(<Event />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создать")).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText("Название"), "Test Event")
    await user.type(screen.getByLabelText("Дата начала"), "2026-04-01")
    await user.type(screen.getByLabelText("Дата окончания"), "2026-04-02")

    await user.click(screen.getByText("Создать"))

    await waitFor(() => {
      expect(mockCreateEvent).toHaveBeenCalled()
    })
  })
})
