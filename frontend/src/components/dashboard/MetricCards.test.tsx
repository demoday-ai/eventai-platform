import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MetricCards } from "./MetricCards"
import type { DashboardData } from "../../lib/api-client"

const mockData: DashboardData = {
  event: null,
  projects: { total: 42 },
  students: { total: 100, confirmed: 80, pending: 15, declined: 5 },
  experts: { total: 50, confirmed: 40, pending: 10, invited: 45 },
  partners: { total: 12, from_bot: 8, from_import: 4 },
  guests: { total: 30, by_subtype: [] },
  rooms: { total: 6, with_experts: 5, without_experts: 1 },
  alerts: [],
}

describe("MetricCards", () => {
  it("renders 5 metric cards with correct values", () => {
    render(<MetricCards data={mockData} loading={false} />)
    expect(screen.getByText("42")).toBeInTheDocument()   // projects
    expect(screen.getByText("100")).toBeInTheDocument()  // students
    expect(screen.getByText("50")).toBeInTheDocument()   // experts
    expect(screen.getByText("12")).toBeInTheDocument()   // partners
    expect(screen.getByText("6")).toBeInTheDocument()    // rooms
  })

  it("renders card titles", () => {
    render(<MetricCards data={mockData} loading={false} />)
    expect(screen.getByText("Проекты")).toBeInTheDocument()
    expect(screen.getByText("Студенты")).toBeInTheDocument()
    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Партнёры")).toBeInTheDocument()
    expect(screen.getByText("Залы")).toBeInTheDocument()
  })

  it("renders loading skeletons when loading", () => {
    const { container } = render(<MetricCards data={undefined} loading={true} />)
    const skeletons = container.querySelectorAll(".animate-pulse")
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("renders zero values when data has zeroes", () => {
    const emptyData: DashboardData = {
      event: null,
      projects: { total: 0 },
      students: { total: 0, confirmed: 0, pending: 0, declined: 0 },
      experts: { total: 0, confirmed: 0, pending: 0, invited: 0 },
      partners: { total: 0, from_bot: 0, from_import: 0 },
      guests: { total: 0, by_subtype: [] },
      rooms: { total: 0, with_experts: 0, without_experts: 0 },
      alerts: [],
    }
    render(<MetricCards data={emptyData} loading={false} />)
    const zeroes = screen.getAllByText("0")
    expect(zeroes.length).toBe(5)
  })
})
