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
const mockSuggestRoomThemes = vi.fn()

const mockGetProjects = vi.fn()

vi.mock("../lib/api-client", () => ({
  runClustering: (...args: unknown[]) => mockRunClustering(...args),
  getCurrentClustering: (...args: unknown[]) => mockGetCurrentClustering(...args),
  getClusteringJobStatus: (...args: unknown[]) => mockGetClusteringJobStatus(...args),
  moveProject: (...args: unknown[]) => mockMoveProject(...args),
  approveClustering: (...args: unknown[]) => mockApproveClustering(...args),
  suggestRoomThemes: (...args: unknown[]) => mockSuggestRoomThemes(...args),
  getProjects: (...args: unknown[]) => mockGetProjects(...args),
}))

let testQueryClient: QueryClient

const createWrapper = () => {
  testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={testQueryClient}>
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

  it("shows approved state with next-step hint", async () => {
    mockGetCurrentClustering.mockResolvedValue({
      ...mockClusteringResult,
      approved_at: "2026-02-01T12:00:00",
    })

    render(<Clustering />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Кластеризация одобрена")).toBeInTheDocument()
      expect(screen.getByText("Следующий шаг — распределение экспертов")).toBeInTheDocument()
      expect(screen.getByText("Перейти к экспертам")).toHaveAttribute("href", "/experts")
    })
  })

  it("shows confirmation dialog when clicking approve", async () => {
    const user = userEvent.setup()
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)

    render(<Clustering />, { wrapper: createWrapper() })

    // Navigate to approve step
    await waitFor(() => {
      expect(screen.getByText("Далее")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Далее"))

    // Step 2 → Step 3
    await waitFor(() => {
      const nextButtons = screen.getAllByText("Далее")
      expect(nextButtons.length).toBeGreaterThan(0)
    })
    const nextButtons = screen.getAllByText("Далее")
    await user.click(nextButtons[0])

    // Step 3: click Одобрить
    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Одобрить"))

    // Should show confirmation
    await waitFor(() => {
      expect(screen.getByText(/Вы уверены/)).toBeInTheDocument()
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
      expect(screen.getByText("Отмена")).toBeInTheDocument()
    })
  })

  it("invalidates pipeline-status and dashboard after approval", async () => {
    const user = userEvent.setup()
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)
    mockApproveClustering.mockResolvedValue({ status: "approved" })

    render(<Clustering />, { wrapper: createWrapper() })

    const invalidateSpy = vi.spyOn(testQueryClient, "invalidateQueries")

    // Navigate to approve step (step 1 → step 2 → step 3)
    await waitFor(() => {
      expect(screen.getByText("Далее")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Далее"))

    await waitFor(() => {
      const nextButtons = screen.getAllByText("Далее")
      expect(nextButtons.length).toBeGreaterThan(0)
    })
    await user.click(screen.getAllByText("Далее")[0])

    // Click Одобрить → confirm
    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Одобрить"))
    await waitFor(() => {
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(screen.getByText("Кластеризация одобрена")).toBeInTheDocument()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["pipeline-status"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] })
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

describe("Clustering - Suggest Themes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetProjects.mockResolvedValue([{ id: "1", title: "Test Project" }])
    mockGetCurrentClustering.mockResolvedValue(null)
    mockRunClustering.mockResolvedValue({ job_id: "job-1" })
    mockGetClusteringJobStatus.mockResolvedValue({ status: "pending" })
  })

  it("should fill textarea when suggest succeeds", async () => {
    const user = userEvent.setup()
    mockSuggestRoomThemes.mockResolvedValue({
      themes: ["NLP и LLM", "Computer Vision", "AI в финансах"],
    })

    render(<Clustering />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.queryByText(/Для кластеризации необходимы проекты/)).not.toBeInTheDocument())

    const numRoomsInput = screen.getByLabelText(/Количество залов/)
    await user.clear(numRoomsInput)
    await user.type(numRoomsInput, "3")

    const suggestBtn = screen.getByRole("button", { name: /Подсказать тематики/ })
    await user.click(suggestBtn)

    await waitFor(() => {
      expect(mockSuggestRoomThemes).toHaveBeenCalledWith({ num_rooms: 3 })
    })

    const textarea = screen.getByLabelText(/Тематики залов/)
    await waitFor(() => {
      expect(textarea).toHaveValue("NLP и LLM\nComputer Vision\nAI в финансах")
    })
  })

  it("should show error if suggest fails", async () => {
    const user = userEvent.setup()
    mockSuggestRoomThemes.mockRejectedValue(new Error("LLM timeout"))

    render(<Clustering />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.queryByText(/Для кластеризации необходимы проекты/)).not.toBeInTheDocument())

    const suggestBtn = screen.getByRole("button", { name: /Подсказать тематики/ })
    await user.click(suggestBtn)

    await waitFor(() => {
      expect(screen.getByText(/Ошибка подсказки: LLM timeout/)).toBeInTheDocument()
    })
  })
})
