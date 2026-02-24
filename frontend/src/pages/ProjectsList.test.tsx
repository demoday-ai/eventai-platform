import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { ProjectsList } from "./ProjectsList"
import * as apiClient from "../lib/api-client"
import { BackgroundJobsProvider } from "../contexts/BackgroundJobsContext"

// Mock hooks
vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

// Mock API client
vi.mock("../lib/api-client", async () => {
  const actual = await vi.importActual("../lib/api-client")
  return {
    ...actual,
    getProjects: vi.fn(),
    getCoverage: vi.fn(),
  }
})

const mockProjects = [
  {
    id: "project-1",
    title: "Чатбот для поддержки",
    author: "Команда А",
    track: null,
    room_id: "room-1",
    room_name: "Зал 1: NLP",
    start_time: "2026-02-06T10:00:00",
    end_time: "2026-02-06T10:15:00",
    status: "confirmed" as const,
    tags: ["NLP", "Chatbot"],
  },
  {
    id: "project-2",
    title: "Анализ тональности",
    author: "Команда Б",
    track: null,
    room_id: "room-1",
    room_name: "Зал 1: NLP",
    start_time: "2026-02-06T10:15:00",
    end_time: "2026-02-06T10:30:00",
    status: "pending" as const,
    tags: ["NLP", "Sentiment"],
  },
  {
    id: "project-3",
    title: "Распознавание объектов",
    author: "Команда В",
    track: null,
    room_id: "room-2",
    room_name: "Зал 2: CV",
    start_time: "2026-02-06T11:00:00",
    end_time: "2026-02-06T11:15:00",
    status: "confirmed" as const,
    tags: ["CV", "Detection"],
  },
]

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <BackgroundJobsProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    </BackgroundJobsProvider>
  )
}

describe("ProjectsList", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock getCoverage for room filter
    vi.mocked(apiClient.getCoverage).mockResolvedValue([
      {
        room_id: "room-1",
        room_name: "Зал 1: NLP",
        total_experts: 5,
        confirmed_experts: 5,
        projects_count: 20,
        coverage_status: "covered",
      },
      {
        room_id: "room-2",
        room_name: "Зал 2: CV",
        total_experts: 4,
        confirmed_experts: 2,
        projects_count: 18,
        coverage_status: "partial",
      },
    ])
  })

  it("renders loading state initially", () => {
    vi.mocked(apiClient.getProjects).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<ProjectsList />, { wrapper: createWrapper() })

    expect(screen.getByText(/загрузка/i)).toBeInTheDocument()
  })

  it("renders projects list when loaded", async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот для поддержки")).toBeInTheDocument()
      expect(screen.getByText("Анализ тональности")).toBeInTheDocument()
      expect(screen.getByText("Распознавание объектов")).toBeInTheDocument()
    })
  })

  it("renders error state when API fails", async () => {
    vi.mocked(apiClient.getProjects).mockRejectedValue(
      new Error("Projects not found")
    )

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/ошибка/i)).toBeInTheDocument()
    })
  })

  it("displays project details correctly", async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Команда А")).toBeInTheDocument()
      // Room name appears in filter dropdown and in project list
      expect(screen.getAllByText("Зал 1: NLP").length).toBeGreaterThan(0)
    })
  })

  it("displays project tags", async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      // Tags appear multiple times (for each project)
      expect(screen.getAllByText("NLP").length).toBeGreaterThan(0)
      expect(screen.getByText("Chatbot")).toBeInTheDocument()
    })
  })

  it("filters projects by room", async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот для поддержки")).toBeInTheDocument()
    })

    // Wait for room options to load in the select
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Зал 1: NLP" })).toBeInTheDocument()
    })

    // Select room filter
    const roomFilter = screen.getByLabelText(/зал/i)
    await user.selectOptions(roomFilter, "room-1")

    // Should call API with room filter
    await waitFor(() => {
      expect(apiClient.getProjects).toHaveBeenCalledWith({ room_id: "room-1" })
    })
  })

  it("filters projects by status", async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот для поддержки")).toBeInTheDocument()
    })

    // Wait for status options to render in the select
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Подтверждён" })).toBeInTheDocument()
    })

    // Select status filter
    const statusFilter = screen.getByLabelText(/статус/i)
    await user.selectOptions(statusFilter, "confirmed")

    // Should call API with status filter
    await waitFor(() => {
      expect(apiClient.getProjects).toHaveBeenCalledWith({ status: "confirmed" })
    })
  })

  it("searches projects by title", async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот для поддержки")).toBeInTheDocument()
    })

    // Type in search
    const searchInput = screen.getByPlaceholderText(/поиск/i)

    // Clear input first and use paste for instant update
    await user.clear(searchInput)
    await user.click(searchInput)
    await user.paste("чатбот")

    // Should call API with search param
    await waitFor(() => {
      const calls = vi.mocked(apiClient.getProjects).mock.calls
      // Find a call with the full search term
      const matchingCall = calls.find(call => call[0]?.search === "чатбот")
      expect(matchingCall).toBeDefined()
    }, { timeout: 1000 })
  })

  it("displays project count", async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjects)

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/проекты.*3/i)).toBeInTheDocument()
    })
  })

  it("shows empty state with link to import when no projects and no filters", async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValue([])

    render(<ProjectsList />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Проекты ещё не загружены")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })
})
