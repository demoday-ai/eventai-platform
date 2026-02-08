import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Clustering } from "./Clustering"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockRunClustering = vi.fn()
const mockGetCurrentClustering = vi.fn()
const mockGetClusteringJobStatus = vi.fn()
const mockMoveProject = vi.fn()
const mockApproveClustering = vi.fn()

const mockGetProjects = vi.fn()

vi.mock("../lib/api-client", () => ({
  runClustering: (...args: unknown[]) => mockRunClustering(...args),
  getCurrentClustering: (...args: unknown[]) => mockGetCurrentClustering(...args),
  getClusteringJobStatus: (...args: unknown[]) => mockGetClusteringJobStatus(...args),
  moveProject: (...args: unknown[]) => mockMoveProject(...args),
  approveClustering: (...args: unknown[]) => mockApproveClustering(...args),
  getProjects: (...args: unknown[]) => mockGetProjects(...args),
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

const mockClusteringResult = {
  id: "run-1",
  status: "completed",
  num_rooms: 2,
  feedback: null,
  rooms: [
    {
      id: "room-1",
      name: "Зал 1: NLP",
      theme_rationale: "NLP проекты",
      project_count: 2,
      projects: [
        { id: "p1", title: "Чатбот", description: "", tags: ["NLP"], author: "A", telegram_contact: "", source: "csv", room: null },
        { id: "p2", title: "Переводчик", description: "", tags: ["NLP"], author: "B", telegram_contact: "", source: "csv", room: null },
      ],
    },
    {
      id: "room-2",
      name: "Зал 2: CV",
      theme_rationale: "CV проекты",
      project_count: 1,
      projects: [
        { id: "p3", title: "Детектор", description: "", tags: ["CV"], author: "C", telegram_contact: "", source: "csv", room: null },
      ],
    },
  ],
  created_at: "2026-02-01T10:00:00",
  approved_at: null,
}

describe("Clustering", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetCurrentClustering.mockRejectedValue(new Error("Not found"))
    mockGetProjects.mockResolvedValue([{ id: "p1", title: "Test" }]) // default: projects exist
  })

  it("shows empty state when no projects exist", async () => {
    mockGetProjects.mockResolvedValue([])

    render(<Clustering />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Для кластеризации необходимы проекты")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })

  it("renders parameters step initially", () => {
    render(<Clustering />, { wrapper: createWrapper() })

    expect(screen.getByText("Кластеризация")).toBeInTheDocument()
    expect(screen.getByText("Параметры кластеризации")).toBeInTheDocument()
    expect(screen.getByLabelText("Количество залов (2-20)")).toBeInTheDocument()
    expect(screen.getByText("Запустить")).toBeInTheDocument()
  })

  it("runs clustering and shows results", async () => {
    const user = userEvent.setup()
    // New background job flow: runClustering returns job_id
    mockRunClustering.mockResolvedValue({ job_id: "job-1", status: "pending" })
    // Job status polling returns completed with run_id
    mockGetClusteringJobStatus.mockResolvedValue({
      job_id: "job-1",
      status: "completed",
      result: { run_id: "run-1" },
    })
    // getCurrentClustering called after job completes
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)

    render(<Clustering />, { wrapper: createWrapper() })

    const runBtn = screen.getByText("Запустить")
    await user.click(runBtn)

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByText("Зал 2: CV")).toBeInTheDocument()
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
      expect(screen.getByText("Детектор")).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it("loads existing clustering and shows results", async () => {
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)

    render(<Clustering />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
    })
  })

  it("shows approved state for approved clustering", async () => {
    mockGetCurrentClustering.mockResolvedValue({
      ...mockClusteringResult,
      approved_at: "2026-02-01T12:00:00",
    })

    render(<Clustering />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Кластеризация одобрена")).toBeInTheDocument()
    })
  })

  it("shows error when clustering fails", async () => {
    const user = userEvent.setup()
    mockRunClustering.mockRejectedValue(new Error("Server error"))

    render(<Clustering />, { wrapper: createWrapper() })

    const runBtn = screen.getByText("Запустить")
    await user.click(runBtn)

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })
})
