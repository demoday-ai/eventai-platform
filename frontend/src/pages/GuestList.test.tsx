import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
        has_business_profile: true,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Партнёр")).toBeInTheDocument()
      expect(screen.getByText("@ivanp")).toBeInTheDocument()
    })
  })

  it("shows tag filter chips from guest tags", async () => {
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "Гость 1",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: ["AI", "NLP"],
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
      },
      {
        id: "g2",
        full_name: "Гость 2",
        username: null,
        role: "business",
        guest_subtype: null,
        profile_summary: null,
        tags: ["CV"],
        recommendations_count: 2,
        contact_requests_count: 0,
        has_business_profile: true,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      const tagFilters = screen.getByTestId("tag-filters")
      expect(tagFilters).toBeInTheDocument()
    })

    // All unique tags should be present
    expect(screen.getByRole("button", { name: "AI" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "NLP" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "CV" })).toBeInTheDocument()
  })

  it("filters guests by tag selection", async () => {
    const user = userEvent.setup()
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "NLP Expert",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: ["NLP"],
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
      },
      {
        id: "g2",
        full_name: "CV Expert",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: ["CV"],
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("NLP Expert")).toBeInTheDocument()
      expect(screen.getByText("CV Expert")).toBeInTheDocument()
    })

    // Click NLP tag filter
    await user.click(screen.getByRole("button", { name: "NLP" }))

    await waitFor(() => {
      expect(screen.getByText("NLP Expert")).toBeInTheDocument()
      expect(screen.queryByText("CV Expert")).not.toBeInTheDocument()
    })
  })

  it("filters guests by activity filter", async () => {
    const user = userEvent.setup()
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "With Recs",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: [],
        recommendations_count: 3,
        contact_requests_count: 0,
        has_business_profile: false,
      },
      {
        id: "g2",
        full_name: "No Recs",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: [],
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("With Recs")).toBeInTheDocument()
      expect(screen.getByText("No Recs")).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: "С рекомендациями" }))

    await waitFor(() => {
      expect(screen.getByText("With Recs")).toBeInTheDocument()
      expect(screen.queryByText("No Recs")).not.toBeInTheDocument()
    })
  })

  it("resets all filters on reset button click", async () => {
    const user = userEvent.setup()
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "Гость А",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: ["AI"],
        recommendations_count: 1,
        contact_requests_count: 0,
        has_business_profile: false,
      },
      {
        id: "g2",
        full_name: "Гость Б",
        username: null,
        role: "guest",
        guest_subtype: null,
        profile_summary: null,
        tags: [],
        recommendations_count: 0,
        contact_requests_count: 0,
        has_business_profile: false,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Гость А")).toBeInTheDocument()
    })

    // Apply tag filter
    await user.click(screen.getByRole("button", { name: "AI" }))

    await waitFor(() => {
      expect(screen.queryByText("Гость Б")).not.toBeInTheDocument()
    })

    // Click reset
    await user.click(screen.getByText(/Сбросить/))

    await waitFor(() => {
      expect(screen.getByText("Гость А")).toBeInTheDocument()
      expect(screen.getByText("Гость Б")).toBeInTheDocument()
    })
  })

  it("shows send to segment button when filters are active", async () => {
    const user = userEvent.setup()
    mockGetGuests.mockResolvedValue([
      {
        id: "g1",
        full_name: "Бизнес Иванов",
        username: null,
        role: "business",
        guest_subtype: null,
        profile_summary: null,
        tags: ["AI"],
        recommendations_count: 1,
        contact_requests_count: 0,
        has_business_profile: true,
      },
    ])

    render(<GuestList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Бизнес Иванов")).toBeInTheDocument()
    })

    // No send button without advanced filters
    expect(screen.queryByText("Отправить сегменту")).not.toBeInTheDocument()

    // Apply tag filter
    await user.click(screen.getByRole("button", { name: "AI" }))

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Отправить сегменту/ })).toBeInTheDocument()
      expect(screen.getByRole("link", { name: /Отправить сегменту/ })).toHaveAttribute("href", expect.stringContaining("/messaging"))
    })
  })
})
