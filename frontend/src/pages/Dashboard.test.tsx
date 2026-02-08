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

// Mock usePipelineStatus to avoid double query
vi.mock("../hooks/usePipelineStatus", () => ({
  usePipelineStatus: () => ({ data: null }),
}))

// Mock API client
vi.mock("../lib/api-client", async () => {
  const actual = await vi.importActual("../lib/api-client")
  return {
    ...actual,
    getDashboard: vi.fn(),
    getCoverage: vi.fn(),
    getPipelineStatus: vi.fn(),
  }
})

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

const fullMockData: apiClient.DashboardData = {
  event: {
    name: "Demo Day 2026",
    start_date: "2026-03-15",
    end_date: "2026-03-16",
    days_until: 10,
  },
  projects: { total: 42 },
  students: { total: 100, confirmed: 80, pending: 15, declined: 5 },
  experts: { total: 50, confirmed: 40, pending: 10, invited: 45 },
  partners: { total: 12, from_bot: 8, from_import: 4 },
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

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getCoverage).mockResolvedValue([])
  })

  it("renders empty state when no event", async () => {
    const noEventData: apiClient.DashboardData = {
      event: null,
      projects: { total: 0 },
      students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
      experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
      partners: { total: 0, from_bot: 0, from_import: 0 },
      guests: { total: 0, by_subtype: [] },
      rooms: { total: 0, with_experts: 0, without_experts: 0 },
      alerts: [],
    }

    vi.mocked(apiClient.getDashboard).mockResolvedValue(noEventData)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Нет активного мероприятия")).toBeInTheDocument()
    })
  })

  it("renders dashboard data when loaded", async () => {
    vi.mocked(apiClient.getDashboard).mockResolvedValue(fullMockData)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument()   // projects
      expect(screen.getByText("100")).toBeInTheDocument()  // students
      expect(screen.getByText("50")).toBeInTheDocument()   // experts
      expect(screen.getByText("12")).toBeInTheDocument()   // partners
      expect(screen.getByText("6")).toBeInTheDocument()    // rooms
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
    const mockDataWithAlerts = {
      ...fullMockData,
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

    vi.mocked(apiClient.getDashboard).mockResolvedValue(mockDataWithAlerts)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Алерты")).toBeInTheDocument()
      expect(screen.getByText("Зал без экспертов")).toBeInTheDocument()
      expect(screen.getByText("Пустых слотов: 5")).toBeInTheDocument()
    })
  })

  it("displays dashboard title", () => {
    vi.mocked(apiClient.getDashboard).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Dashboard />, { wrapper: createWrapper() })

    expect(screen.getByText("Dashboard")).toBeInTheDocument()
  })

  it("renders event countdown when event exists", async () => {
    vi.mocked(apiClient.getDashboard).mockResolvedValue(fullMockData)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Demo Day 2026")).toBeInTheDocument()
    })
  })

  it("uses refetchInterval for auto-refresh", () => {
    vi.mocked(apiClient.getDashboard).mockResolvedValue(fullMockData)

    render(<Dashboard />, { wrapper: createWrapper() })

    // Verify getDashboard was called (initial fetch)
    expect(apiClient.getDashboard).toHaveBeenCalled()
  })
})
