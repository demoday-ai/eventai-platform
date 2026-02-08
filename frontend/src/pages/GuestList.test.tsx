import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { GuestList } from "./GuestList"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetGuests = vi.fn()
const mockGetGuestDetail = vi.fn()

vi.mock("../lib/api-client", () => ({
  getGuests: (...args: unknown[]) => mockGetGuests(...args),
  getGuestDetail: (...args: unknown[]) => mockGetGuestDetail(...args),
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

describe("GuestList", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows empty state when no event exists", async () => {
    mockGetGuests.mockRejectedValue(new Error("no active event"))

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создайте мероприятие")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })

  it("shows informational empty state when no guests", async () => {
    mockGetGuests.mockResolvedValue([])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Пока никто не взаимодействовал с ботом")).toBeInTheDocument()
      expect(screen.getByText(/Контакты появятся автоматически/)).toBeInTheDocument()
    })
    // No action button for informational empty state
    expect(screen.queryByRole("link", { name: "Перейти к импорту" })).not.toBeInTheDocument()
  })

  it("shows guest table when guests exist", async () => {
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "Иван Партнёр",
        username: "ivanp",
        role: "business",
        guest_subtype: null,
        profile_summary: "CEO компании",
        tags: ["AI", "NLP"],
        recommendations_count: 3,
        contact_requests_count: 1,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Партнёр")).toBeInTheDocument()
      expect(screen.getByText("@ivanp")).toBeInTheDocument()
    })
  })
})
