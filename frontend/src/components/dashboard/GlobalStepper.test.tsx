import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { GlobalStepper } from "./GlobalStepper"

const mockPipelineData = {
  phases: [
    {
      name: "data", label: "Данные", status: "completed" as const,
      steps: [
        { name: "event", label: "Создать событие", status: "completed" as const },
        { name: "projects", label: "Загрузить проекты", status: "completed" as const },
        { name: "students", label: "Загрузить студентов", status: "completed" as const },
        { name: "experts", label: "Загрузить экспертов", status: "completed" as const },
      ],
    },
    {
      name: "distribution", label: "Распределение", status: "in_progress" as const,
      steps: [
        { name: "clustering", label: "Кластеризация проектов", status: "completed" as const },
        { name: "matching", label: "Распределение экспертов", status: "not_started" as const },
        { name: "schedule", label: "Генерация расписания", status: "not_started" as const },
      ],
    },
    {
      name: "launch", label: "Запуск", status: "not_started" as const,
      steps: [
        { name: "reminders", label: "Настройка напоминаний", status: "not_started" as const },
        { name: "briefing", label: "Отправка брифинга", status: "not_started" as const },
      ],
    },
  ],
  next_action: { step: "matching", label: "Распределите экспертов", link: "/experts" },
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

describe("GlobalStepper", () => {
  it("renders 3 phase labels with counts", () => {
    render(<GlobalStepper />, { wrapper: createWrapper() })
    expect(screen.getByText("Данные 4/4")).toBeInTheDocument()
    expect(screen.getByText("Распределение 1/3")).toBeInTheDocument()
    expect(screen.getByText("Запуск 0/2")).toBeInTheDocument()
  })

  it("click on phase toggles sub-steps", () => {
    render(<GlobalStepper />, { wrapper: createWrapper() })
    // Click on "Данные" phase button
    const buttons = screen.getAllByRole("button")
    fireEvent.click(buttons[0])
    // Sub-steps should appear
    expect(screen.getByText("Создать событие")).toBeInTheDocument()
    expect(screen.getByText("Загрузить проекты")).toBeInTheDocument()
  })

  it("returns null when no data", () => {
    vi.mocked(usePipelineStatus).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof usePipelineStatus>)

    const { container } = render(<GlobalStepper />, { wrapper: createWrapper() })
    expect(container.innerHTML).toBe("")
  })
})
