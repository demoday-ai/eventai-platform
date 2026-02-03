import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Dashboard } from "./Dashboard"
import * as apiClient from "../lib/api-client"

// Mock hooks
vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

// Mock API client
vi.mock("../lib/api-client", () => ({
  getDashboard: vi.fn(),
  getCoverage: vi.fn(),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock for getCoverage
    vi.mocked(apiClient.getCoverage).mockResolvedValue([])
  })

  it("renders loading state initially", () => {
    vi.mocked(apiClient.getDashboard).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )
    vi.mocked(apiClient.getCoverage).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<Dashboard />, { wrapper: createWrapper() })

    // Should have skeleton loaders (4 metric cards with skeletons + 1 coverage table loading)
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)

    // Coverage table still shows "Загрузка..."
    expect(screen.getByText("Загрузка...")).toBeInTheDocument()
  })

  it("renders dashboard data when loaded", async () => {
    const mockData = {
      students: { total: 100, confirmed: 80, pending: 15, declined: 5 },
      experts: { total: 50, confirmed: 40, pending: 10, invited: 45 },
      guests: {
        total: 30,
        by_subtype: [
          { subtype: "Абитуриент", count: 10 },
          { subtype: "AI-практик", count: 20 },
        ],
      },
      rooms: { total: 6, with_experts: 5, without_experts: 1 },
      alerts: [],
    }

    vi.mocked(apiClient.getDashboard).mockResolvedValue(mockData)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("100")).toBeInTheDocument() // Students total
      expect(screen.getByText("50")).toBeInTheDocument() // Experts total
      expect(screen.getByText("30")).toBeInTheDocument() // Guests total
      expect(screen.getByText("6")).toBeInTheDocument() // Rooms total
    })
  })

  it("renders error state when API fails", async () => {
    vi.mocked(apiClient.getDashboard).mockRejectedValue(
      new Error("API Error")
    )

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/Ошибка загрузки данных/)).toBeInTheDocument()
    })
  })

  it("renders alerts when present", async () => {
    const mockData = {
      students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
      experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
      guests: { total: 0, by_subtype: [] },
      rooms: { total: 0, with_experts: 0, without_experts: 0 },
      alerts: [
        {
          severity: "critical" as const,
          message: "Зал без экспертов",
          room_name: "Зал 1",
        },
        {
          severity: "warning" as const,
          message: "Пустых слотов: 5",
        },
      ],
    }

    vi.mocked(apiClient.getDashboard).mockResolvedValue(mockData)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Алерты")).toBeInTheDocument()
      expect(screen.getByText("Зал без экспертов")).toBeInTheDocument()
      expect(screen.getByText("Пустых слотов: 5")).toBeInTheDocument()
    })
  })

  it("displays user telegram ID", () => {
    vi.mocked(apiClient.getDashboard).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Dashboard />, { wrapper: createWrapper() })

    expect(screen.getByText("ID: 123456")).toBeInTheDocument()
  })
})
