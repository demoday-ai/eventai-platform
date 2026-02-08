import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { EventCountdown } from "./EventCountdown"
import type { EventSummary } from "../../lib/api-client"

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return { ...actual, useNavigate: () => vi.fn() }
})

describe("EventCountdown", () => {
  it("renders event name", () => {
    const event: EventSummary = {
      name: "Demo Day 2026",
      start_date: "2026-03-15",
      end_date: "2026-03-16",
      days_until: 10,
    }
    render(<EventCountdown event={event} />, { wrapper: BrowserRouter })
    expect(screen.getByText("Demo Day 2026")).toBeInTheDocument()
  })

  it("shows 'через N дней' for future events", () => {
    const event: EventSummary = {
      name: "Demo Day",
      start_date: "2026-03-15",
      end_date: "2026-03-16",
      days_until: 5,
    }
    render(<EventCountdown event={event} />, { wrapper: BrowserRouter })
    expect(screen.getByText(/через 5 дней/)).toBeInTheDocument()
  })

  it("shows 'сегодня' for today", () => {
    const event: EventSummary = {
      name: "Demo Day",
      start_date: "2026-03-15",
      end_date: "2026-03-15",
      days_until: 0,
    }
    render(<EventCountdown event={event} />, { wrapper: BrowserRouter })
    expect(screen.getByText(/сегодня/)).toBeInTheDocument()
  })

  it("shows 'N дней назад' for past events", () => {
    const event: EventSummary = {
      name: "Demo Day",
      start_date: "2026-01-10",
      end_date: "2026-01-11",
      days_until: -3,
    }
    render(<EventCountdown event={event} />, { wrapper: BrowserRouter })
    expect(screen.getByText(/3 дня назад/)).toBeInTheDocument()
  })

  it("handles singular day correctly", () => {
    const event: EventSummary = {
      name: "Demo Day",
      start_date: "2026-03-15",
      end_date: "2026-03-15",
      days_until: 1,
    }
    render(<EventCountdown event={event} />, { wrapper: BrowserRouter })
    expect(screen.getByText(/через 1 день/)).toBeInTheDocument()
  })
})
