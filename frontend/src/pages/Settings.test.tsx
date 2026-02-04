import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { Settings } from "./Settings"
import * as apiClient from "../lib/api-client"

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    telegramId: "123456",
    logout: vi.fn(),
  }),
}))

vi.mock("../lib/api-client", () => ({
  getCurrentEvent: vi.fn(),
  updateCurrentEvent: vi.fn(),
}))

const mockEvent: apiClient.Event = {
  id: "event-1",
  name: "Demo Day 2026",
  start_date: "2026-01-22",
  end_date: "2026-01-23",
  description: "Описание мероприятия",
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders title and loading state", () => {
    vi.mocked(apiClient.getCurrentEvent).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Settings />, { wrapper: createWrapper() })

    expect(screen.getByText("Настройки")).toBeInTheDocument()
    expect(screen.getByText("Загрузка...")).toBeInTheDocument()
  })

  it("loads and displays current event data", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText("Мероприятие")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название") as HTMLInputElement
    expect(nameInput.value).toBe("Demo Day 2026")

    const startInput = screen.getByLabelText("Дата начала") as HTMLInputElement
    expect(startInput.value).toBe("2026-01-22")

    const endInput = screen.getByLabelText("Дата окончания") as HTMLInputElement
    expect(endInput.value).toBe("2026-01-23")

    const descInput = screen.getByLabelText("Описание") as HTMLTextAreaElement
    expect(descInput.value).toBe("Описание мероприятия")
  })

  it("calls updateCurrentEvent on save", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockResolvedValue({
      ...mockEvent,
      name: "New Name",
    })

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "New Name")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(apiClient.updateCurrentEvent).toHaveBeenCalledWith(
        expect.objectContaining({ name: "New Name" })
      )
    })
  })

  it("shows error on API load failure", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockRejectedValue(
      new Error("Network error")
    )

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/Ошибка загрузки/)).toBeInTheDocument()
    })
  })

  it("shows error on save failure", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockRejectedValue(
      new Error("Save failed")
    )

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Changed")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/Ошибка/)).toBeInTheDocument()
    })
  })

  it("validates end_date >= start_date", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Дата начала")).toBeInTheDocument()
    })

    const startInput = screen.getByLabelText("Дата начала")
    const endInput = screen.getByLabelText("Дата окончания")

    // Set end date before start date
    fireEvent.change(startInput, { target: { value: "2026-02-10" } })
    fireEvent.change(endInput, { target: { value: "2026-02-05" } })

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    expect(
      screen.getByText("Дата окончания должна быть не раньше даты начала")
    ).toBeInTheDocument()

    // updateCurrentEvent should NOT have been called
    expect(apiClient.updateCurrentEvent).not.toHaveBeenCalled()
  })

  it("shows success message after save", async () => {
    vi.mocked(apiClient.getCurrentEvent).mockResolvedValue(mockEvent)
    vi.mocked(apiClient.updateCurrentEvent).mockResolvedValue(mockEvent)

    render(<Settings />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByLabelText("Название")).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText("Название")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Updated")

    const saveButton = screen.getByRole("button", { name: "Сохранить" })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText("Сохранено")).toBeInTheDocument()
    })
  })
})
