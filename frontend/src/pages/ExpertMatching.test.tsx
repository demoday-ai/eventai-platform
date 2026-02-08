import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { ExpertMatching } from "./ExpertMatching"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockRunMatching = vi.fn()
const mockGetCurrentMatching = vi.fn()
const mockGetCurrentClustering = vi.fn()
const mockMoveExpert = vi.fn()
const mockApproveMatching = vi.fn()
const mockGetInvitePreview = vi.fn()
const mockConfirmInvites = vi.fn()
const mockAssignExpert = vi.fn()

vi.mock("../lib/api-client", () => ({
  runMatching: (...args: unknown[]) => mockRunMatching(...args),
  getCurrentMatching: (...args: unknown[]) => mockGetCurrentMatching(...args),
  getCurrentClustering: (...args: unknown[]) => mockGetCurrentClustering(...args),
  moveExpert: (...args: unknown[]) => mockMoveExpert(...args),
  assignExpert: (...args: unknown[]) => mockAssignExpert(...args),
  approveMatching: (...args: unknown[]) => mockApproveMatching(...args),
  getInvitePreview: (...args: unknown[]) => mockGetInvitePreview(...args),
  confirmInvites: (...args: unknown[]) => mockConfirmInvites(...args),
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

const mockMatchingResult = {
  clustering_run_id: "run-1",
  total_experts: 10,
  matched_experts: 8,
  unmatched_experts: 2,
  rooms: [
    {
      room_id: "room-1",
      room_name: "Зал 1: NLP",
      expert_count: 4,
      experts: [
        { expert_id: "e1", name: "Иван", match_score: 0.95, matching_tags: ["NLP"], is_manual: false },
        { expert_id: "e2", name: "Мария", match_score: 0.8, matching_tags: ["NLP", "LLM"], is_manual: false },
      ],
    },
    {
      room_id: "room-2",
      room_name: "Зал 2: CV",
      expert_count: 4,
      experts: [
        { expert_id: "e3", name: "Пётр", match_score: 0.9, matching_tags: ["CV"], is_manual: false },
      ],
    },
  ],
}

describe("ExpertMatching", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetCurrentMatching.mockRejectedValue(new Error("Not found"))
    mockGetCurrentClustering.mockResolvedValue({ approved_at: "2026-02-01T12:00:00", rooms: [] }) // default: clustering approved
  })

  it("shows empty state when no approved clustering", async () => {
    mockGetCurrentClustering.mockRejectedValue(new Error("Not found"))

    render(<ExpertMatching />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Для матчинга экспертов необходима одобренная кластеризация")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к кластеризации" })).toHaveAttribute("href", "/clustering")
    })
  })

  it("renders run step initially", () => {
    render(<ExpertMatching />, { wrapper: createWrapper() })

    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Запуск матчинга")).toBeInTheDocument()
    expect(screen.getByText("Запустить матчинг")).toBeInTheDocument()
  })

  it("runs matching and shows results", async () => {
    const user = userEvent.setup()
    mockRunMatching.mockResolvedValue(mockMatchingResult)

    render(<ExpertMatching />, { wrapper: createWrapper() })

    const runBtn = screen.getByText("Запустить матчинг")
    await user.click(runBtn)

    await waitFor(() => {
      expect(screen.getByText("Иван")).toBeInTheDocument()
      expect(screen.getByText("Пётр")).toBeInTheDocument()
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByText("Зал 2: CV")).toBeInTheDocument()
    })
  })

  it("loads existing matching results", async () => {
    mockGetCurrentMatching.mockResolvedValue(mockMatchingResult)

    render(<ExpertMatching />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван")).toBeInTheDocument()
    })
  })

  it("shows match scores for experts", async () => {
    const user = userEvent.setup()
    mockRunMatching.mockResolvedValue(mockMatchingResult)

    render(<ExpertMatching />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Запустить матчинг"))

    await waitFor(() => {
      expect(screen.getByText("95%")).toBeInTheDocument()
      expect(screen.getByText("80%")).toBeInTheDocument()
      expect(screen.getByText("90%")).toBeInTheDocument()
    })
  })

  it("shows error when matching fails", async () => {
    const user = userEvent.setup()
    mockRunMatching.mockRejectedValue(new Error("Server error"))

    render(<ExpertMatching />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Запустить матчинг"))

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })
})
