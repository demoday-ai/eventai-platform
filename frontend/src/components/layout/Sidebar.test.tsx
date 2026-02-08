import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Sidebar } from "./Sidebar"

const mockPipelineData = {
  phases: [
    {
      name: "data", label: "Данные", status: "in_progress" as const,
      steps: [
        { name: "event", label: "Создать событие", status: "completed" as const },
        { name: "projects", label: "Загрузить проекты", status: "completed" as const },
        { name: "students", label: "Загрузить студентов", status: "not_started" as const },
        { name: "experts", label: "Загрузить экспертов", status: "not_started" as const },
      ],
    },
    {
      name: "distribution", label: "Распределение", status: "not_started" as const,
      steps: [
        { name: "clustering", label: "Кластеризация", status: "not_started" as const },
        { name: "matching", label: "Матчинг", status: "not_started" as const },
        { name: "schedule", label: "Расписание", status: "not_started" as const },
      ],
    },
    {
      name: "launch", label: "Запуск", status: "not_started" as const,
      steps: [
        { name: "reminders", label: "Напоминания", status: "not_started" as const },
        { name: "briefing", label: "Брифинг", status: "not_started" as const },
      ],
    },
  ],
  next_action: null,
}

vi.mock("../../hooks/usePipelineStatus", () => ({
  usePipelineStatus: vi.fn(() => ({ data: mockPipelineData })),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("Sidebar", () => {
  it("renders Dashboard as standalone top item", () => {
    render(<Sidebar />, { wrapper: createWrapper() })
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
  })

  it("renders all navigation groups", () => {
    render(<Sidebar />, { wrapper: createWrapper() })
    expect(screen.getByText("Подготовка")).toBeInTheDocument()
    expect(screen.getByText("Распределение")).toBeInTheDocument()
    expect(screen.getByText("Коммуникация")).toBeInTheDocument()
    expect(screen.getByText("Аналитика")).toBeInTheDocument()
    expect(screen.getByText("Администрирование")).toBeInTheDocument()
  })

  it("renders nav items with correct labels", () => {
    render(<Sidebar />, { wrapper: createWrapper() })
    expect(screen.getByText("Импорт данных")).toBeInTheDocument()
    expect(screen.getByText("Кластеризация")).toBeInTheDocument()
    expect(screen.getByText("Эксперты")).toBeInTheDocument()
    expect(screen.getByText("Расписание")).toBeInTheDocument()
    expect(screen.getByText("Рассылки")).toBeInTheDocument()
    expect(screen.getByText("Покрытие")).toBeInTheDocument()
    expect(screen.getByText("Аудитория")).toBeInTheDocument()
    expect(screen.getByText("Настройки")).toBeInTheDocument()
  })

  it("renders status badges for pipeline items", () => {
    const { container } = render(<Sidebar />, { wrapper: createWrapper() })
    // Import has some steps completed (attention badge — yellow)
    const badges = container.querySelectorAll(".rounded-full")
    expect(badges.length).toBeGreaterThan(0)
  })

  it("shows attention badge for partially completed import", () => {
    const { container } = render(<Sidebar />, { wrapper: createWrapper() })
    // The import item has 2/4 steps completed → attention (yellow)
    const yellowBadges = container.querySelectorAll(".bg-yellow-500")
    expect(yellowBadges.length).toBeGreaterThanOrEqual(1)
  })
})
