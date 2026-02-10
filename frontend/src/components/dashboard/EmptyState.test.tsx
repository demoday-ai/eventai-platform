import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { EmptyState } from "./EmptyState"

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe("EmptyState", () => {
  it("renders empty state message", () => {
    render(<EmptyState />, { wrapper: BrowserRouter })
    expect(screen.getByText("Нет активного мероприятия")).toBeInTheDocument()
  })

  it("renders create event button", () => {
    render(<EmptyState />, { wrapper: BrowserRouter })
    expect(screen.getByText("Создать мероприятие")).toBeInTheDocument()
  })

  it("navigates to /event on button click", () => {
    render(<EmptyState />, { wrapper: BrowserRouter })
    fireEvent.click(screen.getByText("Создать мероприятие"))
    expect(mockNavigate).toHaveBeenCalledWith("/event")
  })
})
