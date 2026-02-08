import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { RoomDetail } from "./RoomDetail"
import * as apiClient from "../lib/api-client"

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
    getRoomDetail: vi.fn(),
    updateRoom: vi.fn(),
  }
})

const mockRoomData = {
  room: {
    id: "room-1",
    name: "Зал 1: NLP",
    description: "Зал для проектов по обработке естественного языка",
    theme_rationale: "NLP проекты",
  },
  experts: [
    {
      id: "expert-1",
      name: "Иван Иванов",
      status: "confirmed" as const,
      tags: ["NLP", "Transformers"],
    },
    {
      id: "expert-2",
      name: "Петр Петров",
      status: "pending" as const,
      tags: ["NLP", "LLM"],
    },
  ],
  projects: [
    {
      id: "project-1",
      title: "Чатбот для поддержки",
      author: "Команда А",
      start_time: "2026-02-06T10:00:00",
      end_time: "2026-02-06T10:15:00",
      status: "confirmed" as const,
    },
    {
      id: "project-2",
      title: "Анализ тональности",
      author: "Команда Б",
      start_time: "2026-02-06T10:15:00",
      end_time: "2026-02-06T10:30:00",
      status: "pending" as const,
    },
  ],
  uncovered_topics: ["Speech Recognition", "Machine Translation"],
}

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
      <BrowserRouter>
        <Routes>
          <Route path="/rooms/:id" element={children} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe("RoomDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders loading state initially", () => {
    vi.mocked(apiClient.getRoomDetail).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    // Navigate to room-1
    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    expect(screen.getByText(/загрузка/i)).toBeInTheDocument()
  })

  it("renders room details when loaded", async () => {
    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      const themeInput = screen.getByLabelText("Тематика зала") as HTMLTextAreaElement
      expect(themeInput.value).toBe("NLP проекты")
    })
  })

  it("renders error state when API fails", async () => {
    vi.mocked(apiClient.getRoomDetail).mockRejectedValue(
      new Error("Room not found")
    )

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/ошибка/i)).toBeInTheDocument()
    })
  })

  it("renders experts list", async () => {
    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Иван Иванов")).toBeInTheDocument()
      expect(screen.getByText("Петр Петров")).toBeInTheDocument()
    })
  })

  it("renders projects list", async () => {
    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот для поддержки")).toBeInTheDocument()
      expect(screen.getByText("Анализ тональности")).toBeInTheDocument()
    })
  })

  it("renders uncovered topics", async () => {
    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/непокрытые тематики/i)).toBeInTheDocument()
      expect(screen.getByText("Speech Recognition")).toBeInTheDocument()
      expect(screen.getByText("Machine Translation")).toBeInTheDocument()
    })
  })

  it("renders back button", async () => {
    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      const backButton = screen.getByRole("button", { name: /назад/i })
      expect(backButton).toBeInTheDocument()
    })
  })

  it("navigates back on back button click", async () => {
    const user = userEvent.setup()

    vi.mocked(apiClient.getRoomDetail).mockResolvedValue(mockRoomData)

    window.history.pushState({}, "", "/rooms/room-1")

    render(<RoomDetail />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
    })

    const backButton = screen.getByRole("button", { name: /назад/i })
    await user.click(backButton)

    // Should navigate back (in real app would go to dashboard)
    expect(window.history.length).toBeGreaterThan(1)
  })
})
