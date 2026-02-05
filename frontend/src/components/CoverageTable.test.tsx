import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { BrowserRouter } from "react-router-dom"
import { CoverageTable } from "./CoverageTable"

const mockCoverageData = [
  {
    room_id: "room-1",
    room_name: "Зал 1: NLP",
    total_experts: 5,
    confirmed_experts: 5,
    projects_count: 20,
    coverage_status: "full" as const,
  },
  {
    room_id: "room-2",
    room_name: "Зал 2: CV",
    total_experts: 4,
    confirmed_experts: 2,
    projects_count: 18,
    coverage_status: "partial" as const,
  },
  {
    room_id: "room-3",
    room_name: "Зал 3: Agents",
    total_experts: 0,
    confirmed_experts: 0,
    projects_count: 15,
    coverage_status: "none" as const,
  },
]

const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>{children}</BrowserRouter>
  )
}

describe("CoverageTable", () => {
  it("renders table headers", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    // Check headers using role
    const headers = screen.getAllByRole("columnheader")
    const headerTexts = headers.map((h) => h.textContent)

    expect(headerTexts).toContain("Зал")
    expect(headerTexts).toContain("Проектов")
    expect(headerTexts).toContain("Эксперты")
    expect(headerTexts).toContain("Статус")
    expect(headerTexts).toContain("Детали")
  })

  it("renders all rooms", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    expect(screen.getByText("Зал 1: NLP")).toBeInTheDocument()
    expect(screen.getByText("Зал 2: CV")).toBeInTheDocument()
    expect(screen.getByText("Зал 3: Agents")).toBeInTheDocument()
  })

  it("displays correct project counts", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    expect(screen.getByText("20")).toBeInTheDocument()
    expect(screen.getByText("18")).toBeInTheDocument()
    expect(screen.getByText("15")).toBeInTheDocument()
  })

  it("displays correct expert counts", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    // Full coverage: 5/5
    expect(screen.getByText(/5 \/ 5/)).toBeInTheDocument()
    // Partial coverage: 2/4
    expect(screen.getByText(/2 \/ 4/)).toBeInTheDocument()
    // No coverage: 0/0
    expect(screen.getByText(/0 \/ 0/)).toBeInTheDocument()
  })

  it("shows correct status indicators", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    // Should have green, yellow, red indicators
    const rows = screen.getAllByRole("row")

    // Row 1 (header) + 3 data rows
    expect(rows).toHaveLength(4)

    // Check for status text labels
    expect(screen.getByText("Покрыт")).toBeInTheDocument() // full
    expect(screen.getByText("Частично")).toBeInTheDocument() // partial
    expect(screen.getByText("Не покрыт")).toBeInTheDocument() // none
  })

  it("renders detail buttons for each room", () => {
    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    const buttons = screen.getAllByRole("button", { name: /детали/i })
    expect(buttons).toHaveLength(3)
  })

  it("navigates to room detail on button click", async () => {
    const user = userEvent.setup()

    render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    const firstButton = screen.getAllByRole("button", { name: /детали/i })[0]
    await user.click(firstButton)

    // Check if navigation happened (URL should change)
    expect(window.location.pathname).toContain("/rooms/room-1")
  })

  it("shows empty state when no data", () => {
    render(<CoverageTable data={[]} />, { wrapper: createWrapper() })

    expect(screen.getByText(/нет данных/i)).toBeInTheDocument()
  })

  it("applies correct CSS classes for coverage status", () => {
    const { container } = render(<CoverageTable data={mockCoverageData} />, {
      wrapper: createWrapper(),
    })

    // Check that status indicators have appropriate styling
    const statusElements = container.querySelectorAll("[data-status]")

    expect(statusElements[0]).toHaveAttribute("data-status", "full")
    expect(statusElements[1]).toHaveAttribute("data-status", "partial")
    expect(statusElements[2]).toHaveAttribute("data-status", "none")
  })
})
