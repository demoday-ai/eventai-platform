import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { DashboardCoverageTable } from "./CoverageTable"
import type { RoomCoverage } from "../../lib/api-client"

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockData: RoomCoverage[] = [
  {
    room_id: "r1", room_name: "Зал 1",
    total_experts: 3, confirmed_experts: 0, projects_count: 10,
    coverage_status: "gap",
  },
  {
    room_id: "r2", room_name: "Зал 2",
    total_experts: 3, confirmed_experts: 1, projects_count: 8,
    coverage_status: "partial",
  },
  {
    room_id: "r3", room_name: "Зал 3",
    total_experts: 3, confirmed_experts: 2, projects_count: 12,
    coverage_status: "covered",
  },
  {
    room_id: "r4", room_name: "Зал 4",
    total_experts: 4, confirmed_experts: 3, projects_count: 6,
    coverage_status: "excellent",
  },
  {
    room_id: "r5", room_name: "Зал 5",
    total_experts: 5, confirmed_experts: 5, projects_count: 4,
    coverage_status: "excess",
  },
]

describe("DashboardCoverageTable", () => {
  it("renders room rows", () => {
    render(<DashboardCoverageTable data={mockData} />, { wrapper: BrowserRouter })
    expect(screen.getByText("Зал 1")).toBeInTheDocument()
    expect(screen.getByText("Зал 5")).toBeInTheDocument()
  })

  it("renders correct status labels", () => {
    render(<DashboardCoverageTable data={mockData} />, { wrapper: BrowserRouter })
    expect(screen.getByText("Пробел")).toBeInTheDocument()
    expect(screen.getByText("Частично")).toBeInTheDocument()
    expect(screen.getByText("Покрыт")).toBeInTheDocument()
    expect(screen.getByText("Отлично")).toBeInTheDocument()
    expect(screen.getByText("Перебор")).toBeInTheDocument()
  })

  it("renders Детали buttons", () => {
    render(<DashboardCoverageTable data={mockData} />, { wrapper: BrowserRouter })
    const buttons = screen.getAllByText("Детали")
    expect(buttons.length).toBe(5)
  })

  it("navigates on Детали click", () => {
    render(<DashboardCoverageTable data={mockData} />, { wrapper: BrowserRouter })
    const buttons = screen.getAllByText("Детали")
    fireEvent.click(buttons[0])
    expect(mockNavigate).toHaveBeenCalledWith("/coverage?room=r1")
  })

  it("returns null for empty data", () => {
    const { container } = render(<DashboardCoverageTable data={[]} />, { wrapper: BrowserRouter })
    expect(container.innerHTML).toBe("")
  })
})
