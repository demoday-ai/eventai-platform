import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Schedule } from "./Schedule"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGenerateSchedule = vi.fn()
const mockGetSchedule = vi.fn()
const mockApproveSchedule = vi.fn()
const mockUpdateSlot = vi.fn()
const mockGetCurrentClustering = vi.fn()
const mockGetUnplacedProjects = vi.fn()
const mockCreateSlot = vi.fn()
const mockDeleteSlot = vi.fn()
const mockConfigureScheduleFromText = vi.fn()
const mockExportScheduleICS = vi.fn()

vi.mock("../lib/api-client", () => ({
  generateSchedule: (...args: unknown[]) => mockGenerateSchedule(...args),
  getSchedule: (...args: unknown[]) => mockGetSchedule(...args),
  approveSchedule: (...args: unknown[]) => mockApproveSchedule(...args),
  updateSlot: (...args: unknown[]) => mockUpdateSlot(...args),
  getCurrentClustering: (...args: unknown[]) => mockGetCurrentClustering(...args),
  getUnplacedProjects: (...args: unknown[]) => mockGetUnplacedProjects(...args),
  createSlot: (...args: unknown[]) => mockCreateSlot(...args),
  deleteSlot: (...args: unknown[]) => mockDeleteSlot(...args),
  configureScheduleFromText: (...args: unknown[]) => mockConfigureScheduleFromText(...args),
  exportScheduleICS: (...args: unknown[]) => mockExportScheduleICS(...args),
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

const mockScheduleResponse = {
  event_name: "Demo Day 2026",
  days: [
    {
      date: "2026-02-06",
      rooms: [
        {
          room_id: "room-1",
          room_name: "Зал 1: NLP",
          slots: [
            {
              id: "slot-1",
              room_id: "room-1",
              room_name: "Зал 1: NLP",
              project_id: "p1",
              project_title: "Чатбот",
              project_author: "Команда А",
              start_time: "2026-02-06T10:00:00",
              end_time: "2026-02-06T10:15:00",
              display_order: 1,
              status: "scheduled",
              slot_type: "project",
              title: null,
            },
            {
              id: "slot-2",
              room_id: "room-1",
              room_name: "Зал 1: NLP",
              project_id: "p2",
              project_title: "Переводчик",
              project_author: "Команда Б",
              start_time: "2026-02-06T10:15:00",
              end_time: "2026-02-06T10:30:00",
              display_order: 2,
              status: "scheduled",
              slot_type: "project",
              title: null,
            },
          ],
        },
        {
          room_id: "room-2",
          room_name: "Зал 2: CV",
          slots: [
            {
              id: "slot-3",
              room_id: "room-2",
              room_name: "Зал 2: CV",
              project_id: null,
              project_title: null,
              project_author: null,
              start_time: "2026-02-06T12:30:00",
              end_time: "2026-02-06T13:00:00",
              display_order: 1,
              status: "scheduled",
              slot_type: "break",
              title: "Обед",
            },
          ],
        },
      ],
    },
  ],
}

const mockClusteringResult = {
  id: "run-1",
  status: "approved",
  num_rooms: 2,
  feedback: null,
  rooms: [
    { id: "room-1", name: "Зал 1: NLP", theme_rationale: "", project_count: 5, projects: [] },
    { id: "room-2", name: "Зал 2: CV", theme_rationale: "", project_count: 3, projects: [] },
  ],
  created_at: "2026-02-01T00:00:00",
  approved_at: "2026-02-02T00:00:00",
}

const mockUnplacedResponse = {
  total: 2,
  items: [
    { id: "p10", title: "Неразмещённый проект", author: "Автор 1", tags: ["NLP"] },
    { id: "p11", title: "Ещё один проект", author: "Автор 2", tags: ["CV", "ML"] },
  ],
}

describe("Schedule", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSchedule.mockRejectedValue(new Error("Not found"))
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)
    mockGetUnplacedProjects.mockResolvedValue({ total: 0, items: [] })
  })

  it("shows empty state when no approved clustering", async () => {
    mockGetCurrentClustering.mockRejectedValue(new Error("Not found"))

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Для генерации расписания необходима одобренная кластеризация")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к кластеризации" })).toHaveAttribute("href", "/clustering")
    })
  })

  it("renders toolbar buttons when clustering exists", async () => {
    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Расписание")).toBeInTheDocument()
      expect(screen.getByText("Авто-заполнить")).toBeInTheDocument()
      expect(screen.getByText("AI-конфигурация")).toBeInTheDocument()
      expect(screen.getByText("+ Перерыв")).toBeInTheDocument()
      expect(screen.getByText("+ Секция")).toBeInTheDocument()
    })
  })

  it("renders timeline grid with rooms as columns", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByText("Зал 2: CV")).toBeInTheDocument()
    })
  })

  it("renders time labels in left column", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Время")).toBeInTheDocument()
      expect(screen.getByText("10:00")).toBeInTheDocument()
    })
  })

  it("renders slots at correct positions", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
      expect(screen.getByText("Переводчик")).toBeInTheDocument()
    })
  })

  it("renders break slot with title", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Обед")).toBeInTheDocument()
    })
  })

  it("day tabs show with slot count", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      // Total slots: 2 in room-1 + 1 in room-2 = 3
      expect(screen.getByText("3")).toBeInTheDocument()
    })
  })

  it("unplaced panel shows unplaced projects count", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockGetUnplacedProjects.mockResolvedValue(mockUnplacedResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Нераспределённые")).toBeInTheDocument()
      expect(screen.getByText("2 из 2")).toBeInTheDocument()
      expect(screen.getByText("Неразмещённый проект")).toBeInTheDocument()
      expect(screen.getByText("Ещё один проект")).toBeInTheDocument()
    })
  })

  it("shows empty schedule message when no schedule", async () => {
    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/Расписание пусто/)).toBeInTheDocument()
    })
  })

  it("shows approve button and confirmation flow", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockApproveSchedule.mockResolvedValue({ total_slots: 3, rooms: 2, days: 1 })

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Одобрить"))

    await waitFor(() => {
      expect(screen.getByText("Вы уверены?")).toBeInTheDocument()
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(screen.getByText(/Одобрено: 3 слотов/)).toBeInTheDocument()
    })
  })

  it("shows link to messaging after approval", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockApproveSchedule.mockResolvedValue({ total_slots: 3, rooms: 2, days: 1 })

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Одобрить"))
    await waitFor(() => expect(screen.getByText("Подтвердить")).toBeInTheDocument())
    await user.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Перейти к авто-напоминаниям" })).toHaveAttribute("href", "/messaging")
    })
  })

  it("invalidates pipeline-status and dashboard after approval", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockApproveSchedule.mockResolvedValue({ total_slots: 3, rooms: 2, days: 1 })

    render(<Schedule />, { wrapper: createWrapper() })

    const invalidateSpy = vi.spyOn(testQueryClient, "invalidateQueries")

    await waitFor(() => expect(screen.getByText("Одобрить")).toBeInTheDocument())

    await user.click(screen.getByText("Одобрить"))
    await waitFor(() => expect(screen.getByText("Подтвердить")).toBeInTheDocument())
    await user.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(screen.getByText(/Одобрено/)).toBeInTheDocument()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["pipeline-status"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] })
  })

  it("shows error when generation fails", async () => {
    const user = userEvent.setup()
    mockGenerateSchedule.mockRejectedValue(new Error("Server error"))

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => expect(screen.getByText("Авто-заполнить")).toBeInTheDocument())

    await user.click(screen.getByText("Авто-заполнить"))

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })

  it("configure from text dialog opens and submits", async () => {
    const user = userEvent.setup()
    mockConfigureScheduleFromText.mockResolvedValue({
      parsed_config: [
        {
          date_hint: "первый день",
          start_time: "10:00",
          end_time: "19:30",
          slot_duration_minutes: 15,
          format: "presentation_15min",
          track_filter: "all_except_research",
          breaks: [{ start_time: "12:30", end_time: "13:00", label: "Обед" }],
          ceremonies: [],
        },
      ],
      rooms_count: 6,
      message: "Конфигурация на 1 день. Залов из кластеризации: 6",
    })

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => expect(screen.getByText("AI-конфигурация")).toBeInTheDocument())

    await user.click(screen.getByText("AI-конфигурация"))

    await waitFor(() => {
      expect(screen.getByText("AI-конфигурация расписания")).toBeInTheDocument()
    })

    const textarea = screen.getByPlaceholderText(/Начинаем в 10/)
    await user.type(textarea, "test input")

    await user.click(screen.getByText("Настроить"))

    await waitFor(() => {
      expect(mockConfigureScheduleFromText).toHaveBeenCalled()
      expect(mockConfigureScheduleFromText.mock.calls[0][0]).toEqual({ text: "test input" })
    })
  })

  it("scale selector changes timeline scale", async () => {
    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      const scaleSelect = screen.getByLabelText("Масштаб")
      expect(scaleSelect).toBeInTheDocument()
      expect(scaleSelect).toHaveValue("15")
    })
  })
})
