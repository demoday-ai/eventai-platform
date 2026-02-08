import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Messaging } from "./Messaging"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockPreviewMessaging = vi.fn()
const mockSendMessaging = vi.fn()
const mockGetCoverage = vi.fn()
const mockGetDashboard = vi.fn()
const mockGetNotificationDashboard = vi.fn()
const mockGetNotifications = vi.fn()
const mockGetScheduleReminderPreview = vi.fn()
const mockSendReminders = vi.fn()
const mockCancelReminders = vi.fn()
const mockGetReminderBatches = vi.fn()
const mockGetReminderBatchDetail = vi.fn()
const mockBroadcastParticipation = vi.fn()
const mockGetParticipationSummary = vi.fn()
const mockGetUnacknowledged = vi.fn()
const mockGetBriefingPreview = vi.fn()
const mockSendBriefing = vi.fn()

vi.mock("../lib/api-client", () => ({
  previewMessaging: (...args: unknown[]) => mockPreviewMessaging(...args),
  sendMessaging: (...args: unknown[]) => mockSendMessaging(...args),
  getCoverage: (...args: unknown[]) => mockGetCoverage(...args),
  getDashboard: (...args: unknown[]) => mockGetDashboard(...args),
  isNoEventError: (error: unknown) => error instanceof Error && error.message.includes("no active event"),
  getNotificationDashboard: (...args: unknown[]) => mockGetNotificationDashboard(...args),
  getNotifications: (...args: unknown[]) => mockGetNotifications(...args),
  getScheduleReminderPreview: (...args: unknown[]) => mockGetScheduleReminderPreview(...args),
  sendReminders: (...args: unknown[]) => mockSendReminders(...args),
  cancelReminders: (...args: unknown[]) => mockCancelReminders(...args),
  getReminderBatches: (...args: unknown[]) => mockGetReminderBatches(...args),
  getReminderBatchDetail: (...args: unknown[]) => mockGetReminderBatchDetail(...args),
  broadcastParticipation: (...args: unknown[]) => mockBroadcastParticipation(...args),
  getParticipationSummary: (...args: unknown[]) => mockGetParticipationSummary(...args),
  getUnacknowledged: (...args: unknown[]) => mockGetUnacknowledged(...args),
  getBriefingPreview: (...args: unknown[]) => mockGetBriefingPreview(...args),
  sendBriefing: (...args: unknown[]) => mockSendBriefing(...args),
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

describe("Messaging", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDashboard.mockResolvedValue({
      students: { total: 10 },
      experts: { total: 5 },
      guests: { total: 3 },
      partners: { total: 2 },
    })
    mockGetNotificationDashboard.mockResolvedValue({
      summary: { total: 0, sent: 0, failed: 0, pending: 0 },
      by_role: [],
      by_type: [],
      unreachable: [],
    })
    mockGetNotifications.mockResolvedValue({ items: [], total: 0 })
    mockGetReminderBatches.mockResolvedValue({ batches: [] })
    mockGetParticipationSummary.mockResolvedValue({
      total: 0, acknowledged: 0, pending: 0, unregistered: 0, by_room: [],
    })
    mockGetUnacknowledged.mockResolvedValue({ items: [] })
  })

  it("shows empty state when no event exists", async () => {
    mockGetDashboard.mockRejectedValue(new Error("no active event"))

    render(<Messaging />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Создайте мероприятие")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })

  it("shows empty state when no participants", async () => {
    mockGetDashboard.mockResolvedValue({
      students: { total: 0 },
      experts: { total: 0 },
      guests: { total: 0 },
      partners: { total: 0 },
    })

    render(<Messaging />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Загрузите участников")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: "Перейти к импорту" })).toHaveAttribute("href", "/import")
    })
  })

  it("renders page title and tabs", () => {
    render(<Messaging />, { wrapper: createWrapper() })

    expect(screen.getByText("Рассылки")).toBeInTheDocument()
    expect(screen.getByText("Обзор")).toBeInTheDocument()
    expect(screen.getByText("Рассылка")).toBeInTheDocument()
    expect(screen.getAllByText("Напоминания").length).toBeGreaterThan(0)
    expect(screen.getByText("Участие")).toBeInTheDocument()
    expect(screen.getByText("Брифинг")).toBeInTheDocument()
  })

  it("shows broadcast tab with role checkboxes", async () => {
    const user = userEvent.setup()
    render(<Messaging />, { wrapper: createWrapper() })

    // Switch to Рассылка tab
    await user.click(screen.getByText("Рассылка"))

    expect(screen.getByText("Студенты")).toBeInTheDocument()
    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Гости")).toBeInTheDocument()
    expect(screen.getByText("Бизнес-партнёры")).toBeInTheDocument()
  })

  it("preview button disabled when no roles selected", async () => {
    const user = userEvent.setup()
    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    const previewButton = screen.getByRole("button", { name: "Предпросмотр" })
    expect(previewButton).toBeDisabled()
  })

  it("preview button disabled when template empty", async () => {
    const user = userEvent.setup()
    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    // Select a role but leave template empty
    await user.click(screen.getByText("Студенты"))

    const previewButton = screen.getByRole("button", { name: "Предпросмотр" })
    expect(previewButton).toBeDisabled()
  })

  it("shows guest subtype dropdown when guest checked", async () => {
    const user = userEvent.setup()
    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    expect(screen.queryByLabelText("Подтип гостей")).not.toBeInTheDocument()

    await user.click(screen.getByText("Гости"))

    expect(screen.getByLabelText("Подтип гостей")).toBeInTheDocument()
  })

  it("shows room filter when expert checked", async () => {
    const user = userEvent.setup()
    mockGetCoverage.mockResolvedValue([
      { room_id: "room-1", room_name: "Зал 1", total_experts: 3, confirmed_experts: 2, projects_count: 5, coverage_status: "full" },
    ])

    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    expect(screen.queryByLabelText("Зал")).not.toBeInTheDocument()

    await user.click(screen.getByText("Эксперты"))

    await waitFor(() => {
      expect(screen.getByLabelText("Зал")).toBeInTheDocument()
    })
  })

  it("loads preview and shows recipient count + sample message", async () => {
    const user = userEvent.setup()
    mockPreviewMessaging.mockResolvedValue({
      recipient_count: 15,
      sample_message: "Здравствуйте, Иван Петров!",
      recipients_preview: [
        { user_id: "u1", full_name: "Иван Петров", role: "student", guest_subtype: null },
      ],
    })

    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    // Select role and type template
    await user.click(screen.getByText("Студенты"))
    await user.type(screen.getByLabelText("Текст сообщения"), "Здравствуйте, {name}!")

    // Click preview
    await user.click(screen.getByRole("button", { name: "Предпросмотр" }))

    await waitFor(() => {
      expect(screen.getByText("15")).toBeInTheDocument()
      expect(screen.getByText("Здравствуйте, Иван Петров!")).toBeInTheDocument()
      expect(screen.getByText(/Иван Петров \(student\)/)).toBeInTheDocument()
    })
  })

  it("sends messages and shows sent/failed/skipped", async () => {
    const user = userEvent.setup()
    mockPreviewMessaging.mockResolvedValue({
      recipient_count: 10,
      sample_message: "Привет, Мария!",
      recipients_preview: [
        { user_id: "u1", full_name: "Мария", role: "student", guest_subtype: null },
      ],
    })
    mockSendMessaging.mockResolvedValue({
      sent: 8,
      failed: 2,
      skipped: 0,
    })

    render(<Messaging />, { wrapper: createWrapper() })

    await user.click(screen.getByText("Рассылка"))

    // Select role and type template
    await user.click(screen.getByText("Студенты"))
    await user.type(screen.getByLabelText("Текст сообщения"), "Привет, {name}!")

    // Preview first
    await user.click(screen.getByRole("button", { name: "Предпросмотр" }))
    await waitFor(() => {
      expect(screen.getByText("Отправить (10)")).toBeInTheDocument()
    })

    // Send
    await user.click(screen.getByRole("button", { name: "Отправить (10)" }))

    await waitFor(() => {
      expect(screen.getByText("Результат рассылки")).toBeInTheDocument()
      expect(screen.getByText("8")).toBeInTheDocument()
      expect(screen.getByText("2")).toBeInTheDocument()
      expect(screen.getByText("0")).toBeInTheDocument()
    })
  })
})
