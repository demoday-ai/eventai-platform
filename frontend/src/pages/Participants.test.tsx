import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Participants } from "./Participants"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetGuests = vi.fn()
const mockExportGuests = vi.fn()

vi.mock("../lib/api-client", () => ({
  getGuests: (...args: unknown[]) => mockGetGuests(...args),
  exportGuests: (...args: unknown[]) => mockExportGuests(...args),
  isNoEventError: (error: unknown) => error instanceof Error && error.message.includes("no active event"),
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

describe("Participants", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls API with source='import'", async () => {
    mockGetGuests.mockResolvedValue([])

    render(<Participants />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockGetGuests).toHaveBeenCalledWith(
        expect.objectContaining({ source: "import" })
      )
    })
  })

  it("shows empty state when no participants loaded", async () => {
    mockGetGuests.mockResolvedValue([])

    render(<Participants />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Участники не загружены")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })

  it("shows no-event empty state", async () => {
    mockGetGuests.mockRejectedValue(new Error("no active event"))

    render(<Participants />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создайте мероприятие")).toBeInTheDocument()
    })
  })

  it("renders participant table", async () => {
    mockGetGuests.mockResolvedValue([
      {
        id: "p1",
        full_name: "Мария Козлова",
        username: "masha_k",
        telegram_user_id: "guest-abc12345",
        role: "guest",
        guest_subtype: "student",
        source: "import",
        tags: [],
        keywords: [],
        profile_summary: null,
        raw_text: null,
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
        created_at: "2026-02-10T10:00:00Z",
      },
      {
        id: "p2",
        full_name: "Дмитрий Горбунов",
        username: "grbn_dima",
        telegram_user_id: "999888777",
        role: "guest",
        guest_subtype: "other",
        source: "import",
        tags: [],
        keywords: [],
        profile_summary: null,
        raw_text: null,
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
        created_at: "2026-02-10T10:00:00Z",
      },
    ])

    render(<Participants />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Мария Козлова")).toBeInTheDocument()
      expect(screen.getByText("@masha_k")).toBeInTheDocument()
      expect(screen.getByText("Дмитрий Горбунов")).toBeInTheDocument()
    })

    // "В боте?" column: guest-abc → "—", 999888777 → "✓"
    const rows = screen.getAllByRole("row")
    // header + 2 data rows
    expect(rows).toHaveLength(3)
    // Second user (real tg id) should show checkmark
    expect(screen.getByText("\u2713")).toBeInTheDocument()
  })

  it("filters by subtype via select", async () => {
    const user = userEvent.setup()
    mockGetGuests.mockResolvedValue([])

    render(<Participants />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Все типы")).toBeInTheDocument()
    })

    // Native select in test environment
    await user.selectOptions(screen.getByRole("combobox"), "student")

    await waitFor(() => {
      expect(mockGetGuests).toHaveBeenCalledWith(
        expect.objectContaining({ source: "import", subtype: "student" })
      )
    })
  })
})
