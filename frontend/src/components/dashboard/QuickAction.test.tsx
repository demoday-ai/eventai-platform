import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { QuickAction } from "./QuickAction"

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const mockPipelineData = {
  phases: [],
  next_action: {
    step: "projects",
    label: "Загрузите проекты на странице Импорта",
    link: "/import",
  },
}

vi.mock("../../hooks/usePipelineStatus", () => ({
  usePipelineStatus: vi.fn(() => ({ data: mockPipelineData })),
}))

import { usePipelineStatus } from "../../hooks/usePipelineStatus"

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("QuickAction", () => {
  it("renders next action label", () => {
    render(<QuickAction />, { wrapper: createWrapper() })
    expect(screen.getByText("Загрузите проекты на странице Импорта")).toBeInTheDocument()
  })

  it("renders navigate button", () => {
    render(<QuickAction />, { wrapper: createWrapper() })
    expect(screen.getByText("Перейти")).toBeInTheDocument()
  })

  it("navigates on button click", () => {
    render(<QuickAction />, { wrapper: createWrapper() })
    fireEvent.click(screen.getByText("Перейти"))
    expect(mockNavigate).toHaveBeenCalledWith("/import")
  })

  it("returns null when next_action is null", () => {
    vi.mocked(usePipelineStatus).mockReturnValue({
      data: { phases: [], next_action: null },
    } as unknown as ReturnType<typeof usePipelineStatus>)

    const { container } = render(<QuickAction />, { wrapper: createWrapper() })
    expect(container.innerHTML).toBe("")
  })
})
