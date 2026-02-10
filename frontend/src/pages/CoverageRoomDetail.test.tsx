import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { CoverageRoomDetail } from "./CoverageRoomDetail"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetRoomCoverageDetail = vi.fn()

vi.mock("../lib/api-client", () => ({
  getRoomCoverageDetail: (...args: unknown[]) => mockGetRoomCoverageDetail(...args),
}))

const createWrapper = (roomId: string) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/experts/rooms/${roomId}`]}>
        <Routes>
          <Route path="/experts/rooms/:roomId" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const mockDetail = {
  room_id: "r1",
  room_name: "Зал 1: NLP",
  project_count: 15,
  project_tags: ["NLP", "Chatbot", "LLM"],
  experts: [
    {
      expert_id: "e1",
      name: "Иванов Иван",
      status: "confirmed",
      match_score: 0.85,
      tags: ["NLP", "LLM"],
      bot_started: true,
    },
    {
      expert_id: "e2",
      name: "Петрова Анна",
      status: "pending",
      match_score: 0.6,
      tags: ["Chatbot"],
      bot_started: false,
    },
  ],
  uncovered_tags: ["Security"],
  candidates: [
    {
      expert_id: "e3",
      name: "Сидоров",
      matching_tags: ["Security"],
      current_rooms: ["Зал 3"],
    },
  ],
}

describe("CoverageRoomDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetRoomCoverageDetail.mockResolvedValue(mockDetail)
  })

  it("renders room detail with experts", async () => {
    render(<CoverageRoomDetail />, { wrapper: createWrapper("r1") })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByText("Иванов Иван")).toBeInTheDocument()
      expect(screen.getByText("Петрова Анна")).toBeInTheDocument()
    })
  })

  it("shows experts list with status and match score", async () => {
    render(<CoverageRoomDetail />, { wrapper: createWrapper("r1") })

    await waitFor(() => {
      expect(screen.getByText("85%")).toBeInTheDocument()
      expect(screen.getByText("60%")).toBeInTheDocument()
      expect(screen.getByText("Запущен")).toBeInTheDocument()
    })
  })

  it("renders back button", async () => {
    render(<CoverageRoomDetail />, { wrapper: createWrapper("r1") })

    await waitFor(() => {
      expect(screen.getByText("← Назад")).toBeInTheDocument()
    })
  })
})
