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

vi.mock("../lib/api-client", () => ({
  generateSchedule: (...args: unknown[]) => mockGenerateSchedule(...args),
  getSchedule: (...args: unknown[]) => mockGetSchedule(...args),
  approveSchedule: (...args: unknown[]) => mockApproveSchedule(...args),
  updateSlot: (...args: unknown[]) => mockUpdateSlot(...args),
  getScheduleChanges: (...args: unknown[]) => mockGetScheduleChanges(...args),
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

describe("Schedule", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSchedule.mockRejectedValue(new Error("Not found"))
    mockGetScheduleChanges.mockResolvedValue({ total: 0, items: [] })
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
})
