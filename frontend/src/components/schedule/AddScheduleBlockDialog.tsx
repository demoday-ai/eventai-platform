import { useState, useEffect } from "react"
import { Button } from "../ui/button"

interface RoomOption {
  room_id: string
  room_name: string
}

export interface BlockSubmitData {
  room_id: string
  start_time: string
  end_time: string
  slot_type: "break" | "section"
  title?: string
}

interface AddScheduleBlockDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: BlockSubmitData) => void
  blockType: "break" | "section"
  rooms: RoomOption[]
  selectedDay: string
}

export function AddScheduleBlockDialog({
  open,
  onClose,
  onSubmit,
  blockType,
  rooms,
  selectedDay,
}: AddScheduleBlockDialogProps) {
  const [roomId, setRoomId] = useState(rooms[0]?.room_id ?? "")
  const [startTime, setStartTime] = useState("")
  const [endTime, setEndTime] = useState("")
  const [title, setTitle] = useState("")

  useEffect(() => {
    if (open) {
      setRoomId(rooms[0]?.room_id ?? "")
      setStartTime("")
      setEndTime("")
      setTitle("")
    }
  }, [open, rooms])

  if (!open) return null

  const dialogTitle = blockType === "break" ? "Добавить перерыв" : "Добавить секцию"
  const needsTitle = blockType === "section"

  const handleSubmit = () => {
    if (needsTitle && !title.trim()) return
    if (!startTime || !endTime || !roomId) return
    if (startTime >= endTime) return

    onSubmit({
      room_id: roomId,
      start_time: `${selectedDay}T${startTime}:00`,
      end_time: `${selectedDay}T${endTime}:00`,
      slot_type: blockType,
      title: needsTitle ? title : undefined,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold mb-4">{dialogTitle}</h2>

        <div className="space-y-3">
          <div>
            <label htmlFor="block-room" className="block text-sm font-medium mb-1">Зал</label>
            <select
              id="block-room"
              className="w-full rounded border px-3 py-2 text-sm"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
            >
              {rooms.map((r) => (
                <option key={r.room_id} value={r.room_id}>{r.room_name}</option>
              ))}
            </select>
          </div>

          {needsTitle && (
            <div>
              <label htmlFor="block-title" className="block text-sm font-medium mb-1">Название</label>
              <input
                id="block-title"
                type="text"
                className="w-full rounded border px-3 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Напр. NLP-блок"
              />
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1">
              <label htmlFor="block-start" className="block text-sm font-medium mb-1">Начало</label>
              <input
                id="block-start"
                type="time"
                className="w-full rounded border px-3 py-2 text-sm"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label htmlFor="block-end" className="block text-sm font-medium mb-1">Конец</label>
              <input
                id="block-end"
                type="time"
                className="w-full rounded border px-3 py-2 text-sm"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <Button variant="outline" onClick={onClose}>Отмена</Button>
          <Button onClick={handleSubmit}>Добавить</Button>
        </div>
      </div>
    </div>
  )
}
