import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SupportChat } from "./SupportChat"

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
