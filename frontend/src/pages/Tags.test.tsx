import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Tags } from "./Tags"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

const mockGetTags = vi.fn()
const mockAddTags = vi.fn()
const mockSuggestTags = vi.fn()
const mockReplaceTags = vi.fn()
const mockDeleteTag = vi.fn()

vi.mock("../lib/api-client", () => ({
  getTags: () => mockGetTags(),
  addTags: (...args: unknown[]) => mockAddTags(...args),
  suggestTags: () => mockSuggestTags(),
  replaceTags: (...args: unknown[]) => mockReplaceTags(...args),
  deleteTag: (...args: unknown[]) => mockDeleteTag(...args),
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

describe("Tags", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page title and tag list", async () => {
    mockGetTags.mockResolvedValue({ tags: ["NLP", "CV", "Agents"] })

    render(<Tags />, { wrapper: createWrapper() })

    expect(screen.getByText("Теги")).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText("NLP")).toBeInTheDocument()
      expect(screen.getByText("CV")).toBeInTheDocument()
      expect(screen.getByText("Agents")).toBeInTheDocument()
    })
  })

  it("shows empty state when no tags", async () => {
    mockGetTags.mockResolvedValue({ tags: [] })

    render(<Tags />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Теги пока не добавлены.")).toBeInTheDocument()
    })
  })

  it("adds tags manually", async () => {
    const user = userEvent.setup()
    mockGetTags.mockResolvedValue({ tags: [] })
    mockAddTags.mockResolvedValue({ added: ["NLP", "CV"], skipped: [] })

    render(<Tags />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Добавить теги вручную")).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText("Добавить теги вручную"), "NLP, CV")
    await user.click(screen.getByRole("button", { name: "Добавить" }))

    await waitFor(() => {
      expect(mockAddTags).toHaveBeenCalled()
    })
  })

  it("shows suggest button and triggers LLM suggestion", async () => {
    const user = userEvent.setup()
    mockGetTags.mockResolvedValue({ tags: [] })
    mockSuggestTags.mockResolvedValue({
      suggested_tags: ["NLP", "CV", "FinTech"],
      project_count: 50,
    })

    render(<Tags />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Предложить теги на основе проектов")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Предложить теги на основе проектов"))

    await waitFor(() => {
      expect(screen.getByText("Предложенные теги (нажмите, чтобы убрать/добавить):")).toBeInTheDocument()
    })
  })

  it("deletes a tag", async () => {
    const user = userEvent.setup()
    mockGetTags.mockResolvedValue({ tags: ["NLP"] })
    mockDeleteTag.mockResolvedValue({})

    render(<Tags />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("NLP")).toBeInTheDocument()
    })

    const deleteBtn = screen.getByTitle("Удалить тег")
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(mockDeleteTag).toHaveBeenCalled()
      expect(mockDeleteTag.mock.calls[0][0]).toBe("NLP")
    })
  })
})
