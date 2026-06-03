import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SupportChat } from "./SupportChat"

// jsdom lacks scrollIntoView; the component calls it on new messages.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

const mockGetConversations = vi.fn()
const mockGetConversationMessages = vi.fn()
const mockReply = vi.fn()
const mockRelease = vi.fn()
const mockClose = vi.fn()

vi.mock("../lib/api-client", () => ({
  getConversations: (...a: unknown[]) => mockGetConversations(...a),
  getConversationMessages: (...a: unknown[]) => mockGetConversationMessages(...a),
  replyToConversation: (...a: unknown[]) => mockReply(...a),
  releaseConversation: (...a: unknown[]) => mockRelease(...a),
  closeConversation: (...a: unknown[]) => mockClose(...a),
}))

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe("SupportChat", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetConversationMessages.mockResolvedValue([])
  })

  it("renders a conversation from the list", async () => {
    mockGetConversations.mockResolvedValue({
      conversations: [{
        user_id: "u1", user_name: "Гость", user_username: "g", user_role: "guest",
        last_message: "привет", last_message_at: null, message_count: 2,
        unread: false, needs_attention: true, taken_over: false, status: "open",
      }],
      total: 1,
    })
    const Wrapper = wrapper()
    render(<Wrapper><SupportChat /></Wrapper>)
    await waitFor(() => expect(screen.getByText("Гость")).toBeInTheDocument())
    // needs_attention badge
    expect(screen.getByText(/Зовёт орга/i)).toBeInTheDocument()
  })

  it("renders assistant message with readable (foreground) text on dark theme", async () => {
    mockGetConversations.mockResolvedValue({
      conversations: [{
        user_id: "u3", user_name: "Гость Три", user_username: null, user_role: "guest",
        last_message: "x", last_message_at: null, message_count: 1,
        unread: false, needs_attention: false, taken_over: false, status: "open",
      }],
      total: 1,
    })
    mockGetConversationMessages.mockResolvedValue([
      { id: "m1", role: "assistant", content: "ответ агента", created_at: "2026-06-03T10:00:00Z" },
    ])
    const Wrapper = wrapper()
    render(<Wrapper><SupportChat /></Wrapper>)
    // select the conversation to open the chat panel
    await waitFor(() => expect(screen.getByText("Гость Три")).toBeInTheDocument())
    await userEvent.click(screen.getByText("Гость Три"))
    const bubble = await screen.findByText("ответ агента")
    const container = bubble.closest("div")!
    // assistant bubble must declare an explicit text color, not inherit a light
    // foreground onto a near-white background (white-on-white bug).
    expect(container.className).toContain("text-foreground")
    expect(container.className.split(/\s+/)).not.toContain("bg-purple-50")
  })

  it("shows date and time on a message, not just time", async () => {
    mockGetConversations.mockResolvedValue({
      conversations: [{
        user_id: "u4", user_name: "Гость Четыре", user_username: null, user_role: "guest",
        last_message: "x", last_message_at: null, message_count: 1,
        unread: false, needs_attention: false, taken_over: false, status: "open",
      }],
      total: 1,
    })
    mockGetConversationMessages.mockResolvedValue([
      { id: "m1", role: "user", content: "вопрос", created_at: "2026-02-06T15:45:00Z" },
    ])
    const Wrapper = wrapper()
    render(<Wrapper><SupportChat /></Wrapper>)
    await waitFor(() => expect(screen.getByText("Гость Четыре")).toBeInTheDocument())
    await userEvent.click(screen.getByText("Гость Четыре"))
    await screen.findByText("вопрос")
    // timestamp must include the date (day + month), not only HH:MM
    expect(screen.getByText(/06\.02|6 февр|06 февр/i)).toBeInTheDocument()
  })

  it("shows takeover badge when taken_over", async () => {
    mockGetConversations.mockResolvedValue({
      conversations: [{
        user_id: "u2", user_name: "Гость Два", user_username: null, user_role: "guest",
        last_message: "x", last_message_at: null, message_count: 1,
        unread: false, needs_attention: false, taken_over: true, status: "open",
      }],
      total: 1,
    })
    const Wrapper = wrapper()
    render(<Wrapper><SupportChat /></Wrapper>)
    await waitFor(() => expect(screen.getByText("Гость Два")).toBeInTheDocument())
    expect(screen.getByText("Перехвачен")).toBeInTheDocument()
  })
})
