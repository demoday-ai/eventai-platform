import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Participation } from "./Participation"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockBroadcastParticipation = vi.fn()
const mockGetParticipationSummary = vi.fn()
const mockGetUnacknowledged = vi.fn()

vi.mock("../lib/api-client", () => ({
  broadcastParticipation: (...args: unknown[]) => mockBroadcastParticipation(...args),
  getParticipationSummary: (...args: unknown[]) => mockGetParticipationSummary(...args),
  getUnacknowledged: (...args: unknown[]) => mockGetUnacknowledged(...args),
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

const mockSummary = {
  total: 50,
  acknowledged: 30,
  pending: 15,
  unregistered: 5,
  by_room: [
    { room_id: "r1", room_name: "Зал 1", total: 25, acknowledged: 15, pending: 10 },
    { room_id: "r2", room_name: "Зал 2", total: 25, acknowledged: 15, pending: 5 },
  ],
}

const mockUnack = {
  items: [
    {
      request_id: "req1",
      project_title: "Проект А",
      author_name: "Автор 1",
      telegram_contact: "@author1",
      room_name: "Зал 1",
      status: "sent",
      sent_at: "2026-02-01T10:00:00",
      reminder_sent: true,
      escalated: false,
    },
  ],
  total: 1,
}

describe("Participation", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetParticipationSummary.mockResolvedValue(mockSummary)
    mockGetUnacknowledged.mockResolvedValue(mockUnack)
  })

  it("renders summary with metric cards", async () => {
    render(<Participation />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Сводка")).toBeInTheDocument()
      expect(screen.getByText("Фильтр по залу")).toBeInTheDocument()
      // Зал 1 appears in filter dropdown, summary table, and unacknowledged table
      expect(screen.getAllByText("Зал 1").length).toBeGreaterThanOrEqual(1)
    })
  })

  it("renders unacknowledged items", async () => {
    render(<Participation />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Проект А")).toBeInTheDocument()
      expect(screen.getByText("Автор 1")).toBeInTheDocument()
    })
  })

  it("sends broadcast and shows result", async () => {
    const user = userEvent.setup()
    mockBroadcastParticipation.mockResolvedValue({
      sent: 10,
      skipped: 2,
      failed: 1,
      unregistered: 3,
      unregistered_projects: ["Проект X"],
    })

    render(<Participation />, { wrapper: createWrapper() })

    const broadcastBtn = screen.getByText("Отправить рассылку")
    await user.click(broadcastBtn)

    await waitFor(() => {
      expect(screen.getByText("Отправлено: 10")).toBeInTheDocument()
    })
  })

  it("shows room filter", async () => {
    render(<Participation />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Фильтр по залу")).toBeInTheDocument()
    })
  })

  it("shows error on summary failure", async () => {
    mockGetParticipationSummary.mockRejectedValue(new Error("fail"))

    render(<Participation />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Ошибка загрузки")).toBeInTheDocument()
    })
  })
})
