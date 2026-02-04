import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Coverage } from "./Coverage"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetCoverageSummary = vi.fn()
const mockGetCoverageGaps = vi.fn()
const mockGetEscalations = vi.fn()
const mockResolveEscalation = vi.fn()

vi.mock("../lib/api-client", () => ({
  getCoverageSummary: (...args: unknown[]) => mockGetCoverageSummary(...args),
  getCoverageGaps: (...args: unknown[]) => mockGetCoverageGaps(...args),
  getEscalations: (...args: unknown[]) => mockGetEscalations(...args),
  resolveEscalation: (...args: unknown[]) => mockResolveEscalation(...args),
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
  rooms: [
    {
      room_id: "r1",
      room_name: "Зал 1: NLP",
      project_count: 20,
      top_tags: ["NLP", "Chatbot"],
      confirmed: 3,
      pending: 1,
      declined: 0,
      total_assigned: 4,
      coverage_level: "full",
    },
  ],
  totals: {
    confirmed: 10,
    pending: 5,
    declined: 2,
    total_needed: 20,
    coverage_percent: 75,
  },
}

describe("Coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetCoverageSummary.mockResolvedValue(mockSummary)
    mockGetCoverageGaps.mockResolvedValue({ total_gaps: 0, gaps: [] })
    mockGetEscalations.mockResolvedValue([])
  })

  it("renders summary tab with metric cards", async () => {
    render(<Coverage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument()
      expect(screen.getByText("75%")).toBeInTheDocument()
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
    })
  })

  it("shows gaps tab content", async () => {
    const user = userEvent.setup()
    mockGetCoverageGaps.mockResolvedValue({
      total_gaps: 1,
      gaps: [
        {
          room_id: "r1",
          room_name: "Зал 1",
          uncovered_tag: "CV",
          project_count_with_tag: 5,
          candidates: [{ expert_id: "e1", name: "Иван", matching_tags: ["CV"], current_rooms: [] }],
        },
      ],
    })

    render(<Coverage />, { wrapper: createWrapper() })

    const gapsTab = screen.getByText("Пробелы")
    await user.click(gapsTab)

    await waitFor(() => {
      expect(screen.getByText("Всего пробелов:")).toBeInTheDocument()
      expect(screen.getByText("CV")).toBeInTheDocument()
    })
  })

  it("shows escalations tab and resolves escalation", async () => {
    const user = userEvent.setup()
    mockGetEscalations.mockResolvedValue([
      {
        id: "esc1",
        type: "no_response",
        expert_name: "Петров",
        room_name: "Зал 2",
        message: "Нет ответа",
        resolved: false,
        created_at: "2026-02-01T10:00:00",
      },
    ])
    mockResolveEscalation.mockResolvedValue({
      id: "esc1",
      type: "no_response",
      expert_name: "Петров",
      room_name: "Зал 2",
      message: "Нет ответа",
      resolved: true,
      created_at: "2026-02-01T10:00:00",
    })

    render(<Coverage />, { wrapper: createWrapper() })

    const escalationsTab = screen.getByText("Эскалации")
    await user.click(escalationsTab)

    await waitFor(() => {
      expect(screen.getByText("Петров")).toBeInTheDocument()
    })

    const resolveBtn = screen.getByText("Решить")
    await user.click(resolveBtn)

    expect(mockResolveEscalation).toHaveBeenCalledWith("esc1")
  })

  it("shows error state on summary failure", async () => {
    mockGetCoverageSummary.mockRejectedValue(new Error("fail"))

    render(<Coverage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Ошибка загрузки данных покрытия")).toBeInTheDocument()
    })
  })

  it("shows details button in room table", async () => {
    render(<Coverage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Детали")).toBeInTheDocument()
    })
  })
})
