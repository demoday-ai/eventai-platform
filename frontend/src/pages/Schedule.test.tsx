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
const mockGetScheduleChanges = vi.fn()
const mockGetCurrentClustering = vi.fn()

vi.mock("../lib/api-client", () => ({
  generateSchedule: (...args: unknown[]) => mockGenerateSchedule(...args),
  getSchedule: (...args: unknown[]) => mockGetSchedule(...args),
  approveSchedule: (...args: unknown[]) => mockApproveSchedule(...args),
  updateSlot: (...args: unknown[]) => mockUpdateSlot(...args),
  getScheduleChanges: (...args: unknown[]) => mockGetScheduleChanges(...args),
  getCurrentClustering: (...args: unknown[]) => mockGetCurrentClustering(...args),
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
    {
      id: "room-1",
      name: "Зал 1: NLP",
      theme_rationale: "",
      project_count: 5,
      projects: [],
    },
    {
      id: "room-2",
      name: "Зал 2: CV",
      theme_rationale: "",
      project_count: 3,
      projects: [],
    },
  ],
  created_at: "2026-02-01T00:00:00",
  approved_at: "2026-02-02T00:00:00",
}

describe("Schedule", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSchedule.mockRejectedValue(new Error("Not found"))
    mockGetScheduleChanges.mockResolvedValue({ total: 0, items: [] })
    mockGetCurrentClustering.mockResolvedValue(mockClusteringResult)
  })

  it("shows empty state when no approved clustering", async () => {
    mockGetCurrentClustering.mockRejectedValue(new Error("Not found"))

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Для генерации расписания необходима одобренная кластеризация")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к кластеризации" })).toHaveAttribute("href", "/clustering")
    })
  })

  it("renders generate step initially", () => {
    render(<Schedule />, { wrapper: createWrapper() })

    expect(screen.getByText("Расписание")).toBeInTheDocument()
    expect(screen.getByText("Генерация расписания")).toBeInTheDocument()
    expect(screen.getByLabelText("Длительность слота (минуты)")).toBeInTheDocument()
    expect(screen.getByText("Сгенерировать")).toBeInTheDocument()
  })

  it("generates schedule and shows result info", async () => {
    const user = userEvent.setup()
    mockGenerateSchedule.mockResolvedValue({
      total_slots: 20,
      rooms: [
        { room_id: "room-1", room_name: "Зал 1", slot_count: 10, first_slot: null, last_slot: null },
        { room_id: "room-2", room_name: "Зал 2", slot_count: 10, first_slot: null, last_slot: null },
      ],
    })
    // After generate, getSchedule will return the schedule
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    const generateBtn = screen.getByText("Сгенерировать")
    await user.click(generateBtn)

    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })
  })

  it("loads existing schedule and shows view", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
      expect(screen.getByText("Переводчик")).toBeInTheDocument()
    })
  })

  it("shows error when generation fails", async () => {
    const user = userEvent.setup()
    mockGenerateSchedule.mockRejectedValue(new Error("Server error"))

    render(<Schedule />, { wrapper: createWrapper() })

    const generateBtn = screen.getByText("Сгенерировать")
    await user.click(generateBtn)

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })

  it("shows slot details in schedule view", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByText("Команда А")).toBeInTheDocument()
      expect(screen.getByText("Команда Б")).toBeInTheDocument()
    })
  })

  it("shows edit button for each slot", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      const editButtons = screen.getAllByTitle("Редактировать")
      expect(editButtons.length).toBe(2)
    })
  })

  it("opens inline edit form on pencil click", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })

    const editBtn = screen.getByLabelText("Редактировать Чатбот")
    await user.click(editBtn)

    await waitFor(() => {
      expect(screen.getByText("Сохранить")).toBeInTheDocument()
      expect(screen.getByText("Отмена")).toBeInTheDocument()
    })
  })

  it("shows change log when data exists", async () => {
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockGetScheduleChanges.mockResolvedValue({
      total: 1,
      items: [
        {
          id: "ch1",
          slot_id: "slot-1",
          project_title: "Чатбот",
          change_type: "time_change",
          old_start_time: "2026-02-06T10:00:00",
          new_start_time: "2026-02-06T11:00:00",
          old_room_name: null,
          new_room_name: null,
          changed_by: "admin",
          created_at: "2026-02-05T15:00:00",
          notifications_sent: 2,
        },
      ],
    })

    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("История изменений")).toBeInTheDocument()
      expect(screen.getByText("time_change")).toBeInTheDocument()
    })
  })

  it("shows per-room time fields from clustering", async () => {
    render(<Schedule />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Время по залам")).toBeInTheDocument()
      expect(screen.getByLabelText("Начало Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByLabelText("Конец Зал 1: NLP")).toBeInTheDocument()
      expect(screen.getByLabelText("Начало Зал 2: CV")).toBeInTheDocument()
      expect(screen.getByLabelText("Конец Зал 2: CV")).toBeInTheDocument()
    })
  })

  it("adds and removes breaks", async () => {
    const user = userEvent.setup()
    render(<Schedule />, { wrapper: createWrapper() })

    const addBtn = await screen.findByText("Добавить перерыв")
    await user.click(addBtn)

    await waitFor(() => {
      expect(screen.getByLabelText("Начало перерыва 1")).toBeInTheDocument()
      expect(screen.getByLabelText("Конец перерыва 1")).toBeInTheDocument()
      expect(screen.getByLabelText("Удалить перерыв 1")).toBeInTheDocument()
    })

    // Remove the break
    await user.click(screen.getByLabelText("Удалить перерыв 1"))

    await waitFor(() => {
      expect(screen.queryByLabelText("Начало перерыва 1")).not.toBeInTheDocument()
    })
  })

  it("shows 'Далее' button on step 0 when schedule exists", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    // Auto-advance takes us to step 1, go back to step 0
    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })

    // Click "Перегенерировать" to go back to step 0
    await user.click(screen.getByText("Перегенерировать"))

    await waitFor(() => {
      expect(screen.getByText("Генерация расписания")).toBeInTheDocument()
    })

    // "Далее" button should be visible since schedule exists
    const nextBtn = screen.getByText("Далее")
    expect(nextBtn).toBeInTheDocument()

    // Click "Далее" to go to step 1
    await user.click(nextBtn)

    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })
  })

  it("shows confirmation dialog when clicking approve", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)

    render(<Schedule />, { wrapper: createWrapper() })

    // Wait for schedule to load (auto-advance to step 1)
    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })

    // Navigate to step 2 (Одобрение)
    await user.click(screen.getByText("Далее"))

    await waitFor(() => {
      expect(screen.getByText("Одобрение расписания")).toBeInTheDocument()
    })

    // Click Одобрить
    await user.click(screen.getByText("Одобрить"))

    // Should show confirmation dialog
    await waitFor(() => {
      expect(screen.getByText(/Вы уверены/)).toBeInTheDocument()
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
      expect(screen.getByText("Отмена")).toBeInTheDocument()
    })
  })

  it("shows next-step hint after approval", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockApproveSchedule.mockResolvedValue({
      total_slots: 2,
      rooms: 1,
      days: 1,
    })

    render(<Schedule />, { wrapper: createWrapper() })

    // Wait for schedule to load
    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })

    // Navigate to approve step
    await user.click(screen.getByText("Далее"))

    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })

    // Click approve, then confirm
    await user.click(screen.getByText("Одобрить"))
    await waitFor(() => {
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Подтвердить"))

    // Should show next-step hint
    await waitFor(() => {
      expect(screen.getByText(/Расписание одобрено/)).toBeInTheDocument()
      expect(screen.getByText("Расписание утверждено. Можно настроить авто-напоминания")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к авто-напоминаниям" })).toHaveAttribute("href", "/messaging")
    })
  })

  it("invalidates pipeline-status and dashboard after approval", async () => {
    const user = userEvent.setup()
    mockGetSchedule.mockResolvedValue(mockScheduleResponse)
    mockApproveSchedule.mockResolvedValue({
      total_slots: 2,
      rooms: 1,
      days: 1,
    })

    render(<Schedule />, { wrapper: createWrapper() })

    const invalidateSpy = vi.spyOn(testQueryClient, "invalidateQueries")

    // Wait for schedule to load
    await waitFor(() => {
      expect(screen.getByText("Чатбот")).toBeInTheDocument()
    })

    // Navigate to approve step
    await user.click(screen.getByText("Далее"))
    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeInTheDocument()
    })

    // Click approve → confirm
    await user.click(screen.getByText("Одобрить"))
    await waitFor(() => {
      expect(screen.getByText("Подтвердить")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Подтвердить"))

    await waitFor(() => {
      expect(screen.getByText(/Расписание одобрено/)).toBeInTheDocument()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["pipeline-status"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] })
  })

  it("passes room_overrides and breaks to generateSchedule", async () => {
    const user = userEvent.setup()
    mockGenerateSchedule.mockResolvedValue({
      total_slots: 10,
      rooms: [{ room_id: "room-1", room_name: "Зал 1", slot_count: 10, first_slot: null, last_slot: null }],
    })
    // Keep schedule empty so we stay on step 0
    mockGetSchedule.mockRejectedValue(new Error("Not found"))

    render(<Schedule />, { wrapper: createWrapper() })

    // Wait for rooms to load
    await waitFor(() => {
      expect(screen.getByText("Время по залам")).toBeInTheDocument()
    })

    // Add a break
    await user.click(screen.getByText("Добавить перерыв"))

    // Click generate
    await user.click(screen.getByText("Сгенерировать"))

    await waitFor(() => {
      expect(mockGenerateSchedule).toHaveBeenCalledWith(
        expect.objectContaining({
          slot_duration_minutes: 15,
          room_overrides: expect.arrayContaining([
            expect.objectContaining({ room_id: "room-1", start_time: "10:30", end_time: "19:30" }),
            expect.objectContaining({ room_id: "room-2", start_time: "10:30", end_time: "19:30" }),
          ]),
          breaks: [{ start_time: "13:00", end_time: "14:00" }],
        })
      )
    })
  })
})
