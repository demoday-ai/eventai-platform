import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Notifications } from "./Notifications"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetNotificationDashboard = vi.fn()
const mockGetNotifications = vi.fn()
const mockGetScheduleReminderPreview = vi.fn()
const mockSendReminders = vi.fn()
const mockCancelReminders = vi.fn()
const mockGetReminderBatches = vi.fn()
const mockGetReminderBatchDetail = vi.fn()

vi.mock("../lib/api-client", () => ({
  getNotificationDashboard: (...args: unknown[]) => mockGetNotificationDashboard(...args),
  getNotifications: (...args: unknown[]) => mockGetNotifications(...args),
  getScheduleReminderPreview: (...args: unknown[]) => mockGetScheduleReminderPreview(...args),
  sendReminders: (...args: unknown[]) => mockSendReminders(...args),
  cancelReminders: (...args: unknown[]) => mockCancelReminders(...args),
  getReminderBatches: (...args: unknown[]) => mockGetReminderBatches(...args),
  getReminderBatchDetail: (...args: unknown[]) => mockGetReminderBatchDetail(...args),
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

const mockDashboard = {
  summary: { total: 100, sent: 90, failed: 5, pending: 5 },
  by_role: [{ role: "student", sent: 50, failed: 2, pending: 3 }],
  by_type: [{ type: "reminder", sent: 60, failed: 3, pending: 2 }],
  unreachable: [],
}

describe("Notifications", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetNotificationDashboard.mockResolvedValue(mockDashboard)
    mockGetNotifications.mockResolvedValue({ total: 0, items: [] })
    mockGetReminderBatches.mockResolvedValue({ batches: [] })
  })

  it("renders dashboard tab with metric cards", async () => {
    render(<Notifications />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("100")).toBeInTheDocument()
      expect(screen.getByText("90")).toBeInTheDocument()
    })
  })

  it("shows notification list tab", async () => {
    const user = userEvent.setup()
    mockGetNotifications.mockResolvedValue({
      total: 1,
      items: [
        {
          id: "n1",
          user_name: "Иван",
          type: "reminder",
          status: "sent",
          scheduled_at: "2026-02-06T08:00:00",
          sent_at: "2026-02-06T08:01:00",
          error_message: null,
          retry_count: 0,
        },
      ],
    })

    render(<Notifications />, { wrapper: createWrapper() })

    // "Уведомления" appears as both h2 and tab button, use getAllByText
    const notifTabs = screen.getAllByText("Уведомления")
    await user.click(notifTabs[1]) // click the tab button (second match)

    await waitFor(() => {
      expect(screen.getByText("Иван")).toBeInTheDocument()
    })
  })

  it("shows reminders tab with preview", async () => {
    const user = userEvent.setup()
    mockGetScheduleReminderPreview.mockResolvedValue({
      day: "2026-02-06",
      scheduled_send_time: "08:00",
      can_cancel: true,
      recipients: { students: 10, experts: 5, guests: 3, business: 2, total: 20 },
      sample_messages: { student: "Привет!", expert: null, guest: null, business: null },
      unreachable: [],
    })

    render(<Notifications />, { wrapper: createWrapper() })

    const remindersTab = screen.getByText("Рассылки")
    await user.click(remindersTab)

    const previewBtn = screen.getByText("Предпросмотр")
    await user.click(previewBtn)

    await waitFor(() => {
      expect(screen.getByText("Итого: 20")).toBeInTheDocument()
    })
  })

  it("sends reminders after preview", async () => {
    const user = userEvent.setup()
    mockGetScheduleReminderPreview.mockResolvedValue({
      day: "2026-02-06",
      scheduled_send_time: "08:00",
      can_cancel: false,
      recipients: { students: 10, experts: 5, guests: 3, business: 2, total: 20 },
      sample_messages: { student: null, expert: null, guest: null, business: null },
      unreachable: [],
    })
    mockSendReminders.mockResolvedValue({ day: "2026-02-06", sent: 18, failed: 1, skipped: 1 })

    render(<Notifications />, { wrapper: createWrapper() })

    const remindersTab = screen.getByText("Рассылки")
    await user.click(remindersTab)

    const previewBtn = screen.getByText("Предпросмотр")
    await user.click(previewBtn)

    await waitFor(() => {
      expect(screen.getByText("Отправить")).toBeInTheDocument()
    })

    const sendBtn = screen.getByText("Отправить")
    await user.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText(/Отправлено: 18/)).toBeInTheDocument()
    })
  })

  it("shows error on dashboard failure", async () => {
    mockGetNotificationDashboard.mockRejectedValue(new Error("fail"))

    render(<Notifications />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Ошибка загрузки дашборда")).toBeInTheDocument()
    })
  })
})
