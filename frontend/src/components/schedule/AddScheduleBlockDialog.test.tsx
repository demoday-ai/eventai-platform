import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { AddScheduleBlockDialog } from "./AddScheduleBlockDialog"

const mockRooms = [
  { room_id: "room-1", room_name: "Зал 1" },
  { room_id: "room-2", room_name: "Зал 2" },
]

describe("AddScheduleBlockDialog", () => {
  it("renders break dialog with correct title", () => {
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        blockType="break"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )
    expect(screen.getByText("Добавить перерыв")).toBeInTheDocument()
  })

  it("renders section dialog with correct title", () => {
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        blockType="section"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )
    expect(screen.getByText("Добавить секцию")).toBeInTheDocument()
  })

  it("requires title for section type", async () => {
    const onSubmit = vi.fn()
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        blockType="section"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )

    const submitBtn = screen.getByRole("button", { name: /добавить/i })
    fireEvent.click(submitBtn)

    // Should not submit without title
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("submits break with room and time", async () => {
    const onSubmit = vi.fn()
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        blockType="break"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )

    // Select room
    const roomSelect = screen.getByLabelText(/зал/i)
    fireEvent.change(roomSelect, { target: { value: "room-1" } })

    // Set times
    const startInput = screen.getByLabelText(/начало/i)
    fireEvent.change(startInput, { target: { value: "12:00" } })

    const endInput = screen.getByLabelText(/конец/i)
    fireEvent.change(endInput, { target: { value: "12:15" } })

    const submitBtn = screen.getByRole("button", { name: /добавить/i })
    fireEvent.click(submitBtn)

    expect(onSubmit).toHaveBeenCalledWith({
      room_id: "room-1",
      start_time: expect.stringContaining("2026-02-22T12:00"),
      end_time: expect.stringContaining("2026-02-22T12:15"),
      slot_type: "break",
      title: undefined,
    })
  })

  it("submits section with title", async () => {
    const onSubmit = vi.fn()
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        blockType="section"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )

    const roomSelect = screen.getByLabelText(/зал/i)
    fireEvent.change(roomSelect, { target: { value: "room-2" } })

    const titleInput = screen.getByLabelText(/название/i)
    fireEvent.change(titleInput, { target: { value: "NLP-блок" } })

    const startInput = screen.getByLabelText(/начало/i)
    fireEvent.change(startInput, { target: { value: "10:30" } })

    const endInput = screen.getByLabelText(/конец/i)
    fireEvent.change(endInput, { target: { value: "13:00" } })

    const submitBtn = screen.getByRole("button", { name: /добавить/i })
    fireEvent.click(submitBtn)

    expect(onSubmit).toHaveBeenCalledWith({
      room_id: "room-2",
      start_time: expect.stringContaining("2026-02-22T10:30"),
      end_time: expect.stringContaining("2026-02-22T13:00"),
      slot_type: "section",
      title: "NLP-блок",
    })
  })

  it("calls onClose when cancel button clicked", () => {
    const onClose = vi.fn()
    render(
      <AddScheduleBlockDialog
        open={true}
        onClose={onClose}
        onSubmit={vi.fn()}
        blockType="break"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )

    const cancelBtn = screen.getByRole("button", { name: /отмена/i })
    fireEvent.click(cancelBtn)

    expect(onClose).toHaveBeenCalled()
  })

  it("does not render when open is false", () => {
    render(
      <AddScheduleBlockDialog
        open={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        blockType="break"
        rooms={mockRooms}
        selectedDay="2026-02-22"
      />
    )

    expect(screen.queryByText("Добавить перерыв")).not.toBeInTheDocument()
  })
})
