import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Briefing } from "./Briefing"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetBriefingPreview = vi.fn()
const mockSendBriefing = vi.fn()

vi.mock("../lib/api-client", () => ({
  getBriefingPreview: (...args: unknown[]) => mockGetBriefingPreview(...args),
  sendBriefing: (...args: unknown[]) => mockSendBriefing(...args),
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

describe("Briefing", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders preview button", () => {
    render(<Briefing />, { wrapper: createWrapper() })

    expect(screen.getByText("Брифинг экспертов")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Предпросмотр" })).toBeInTheDocument()
  })

  it("loads preview and shows expert metrics", async () => {
    const user = userEvent.setup()
    mockGetBriefingPreview.mockResolvedValue({
      expert_count: 10,
      with_telegram: 8,
      without_telegram: 2,
    })

    render(<Briefing />, { wrapper: createWrapper() })

    await user.click(screen.getByRole("button", { name: "Предпросмотр" }))

    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument()
      expect(screen.getByText("8")).toBeInTheDocument()
      expect(screen.getByText("2")).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Отправить брифинги" })).toBeInTheDocument()
    })
  })

  it("sends briefing and shows sent/failed/skipped result", async () => {
    const user = userEvent.setup()
    mockGetBriefingPreview.mockResolvedValue({
      expert_count: 10,
      with_telegram: 8,
      without_telegram: 2,
    })
    mockSendBriefing.mockResolvedValue({
      sent: 7,
      failed: 1,
      skipped: 2,
    })

    render(<Briefing />, { wrapper: createWrapper() })

    // Load preview first
    await user.click(screen.getByRole("button", { name: "Предпросмотр" }))
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Отправить брифинги" })).toBeInTheDocument()
    })

    // Send briefings
    await user.click(screen.getByRole("button", { name: "Отправить брифинги" }))

    await waitFor(() => {
      expect(screen.getByText("Брифинги отправлены")).toBeInTheDocument()
      expect(screen.getByText("7")).toBeInTheDocument()
      expect(screen.getByText("1")).toBeInTheDocument()
    })
  })
})
