import { useState, useEffect } from "react"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import type { ScheduleSlotResponse, SlotUpdateRequest } from "../../lib/api-client"

interface SlotPopoverProps {
  slot: ScheduleSlotResponse
  rooms: { id: string; name: string }[]
  onSave: (slotId: string, body: SlotUpdateRequest) => void
  onDelete: (slotId: string) => void
  onClose: () => void
  isSaving: boolean
}

export function SlotPopover({ slot, rooms, onSave, onDelete, onClose, isSaving }: SlotPopoverProps) {
  const [form, setForm] = useState<SlotUpdateRequest>({
    start_time: slot.start_time,
    end_time: slot.end_time,
    room_id: slot.room_id,
    status: slot.status,
  })

  useEffect(() => {
    setForm({
      start_time: slot.start_time,
      end_time: slot.end_time,
      room_id: slot.room_id,
      status: slot.status,
    })
  }, [slot])

  const slotLabel = slot.slot_type !== "project" && slot.title
    ? slot.title
    : slot.project_title || "Слот"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-lg border shadow-lg p-4 w-80 space-y-3" onClick={(e) => e.stopPropagation()}>
        <h4 className="font-medium text-sm truncate">{slotLabel}</h4>
        {slot.slot_type === "project" && slot.project_author && (
          <p className="text-xs text-muted-foreground">{slot.project_author}</p>
        )}

        <div className="grid gap-2 grid-cols-2">
          <div>
            <Label className="text-xs">Начало</Label>
            <Input
              type="datetime-local"
              value={form.start_time?.slice(0, 16) || ""}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              className="h-7 text-xs"
            />
          </div>
          <div>
            <Label className="text-xs">Конец</Label>
            <Input
              type="datetime-local"
              value={form.end_time?.slice(0, 16) || ""}
              onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              className="h-7 text-xs"
            />
          </div>
        </div>

        <div>
          <Label className="text-xs">Зал</Label>
          <select
            className="w-full rounded-md border px-2 py-1 text-xs"
            value={form.room_id || ""}
            onChange={(e) => setForm({ ...form, room_id: e.target.value })}
          >
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>

        <div>
          <Label className="text-xs">Статус</Label>
          <select
            className="w-full rounded-md border px-2 py-1 text-xs"
            value={form.status || ""}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
          >
            <option value="scheduled">Запланирован</option>
            <option value="moved">Перемещён</option>
            <option value="cancelled">Отменён</option>
          </select>
        </div>

        <div className="flex gap-2 pt-1">
          <Button size="sm" disabled={isSaving} onClick={() => onSave(slot.id, form)}>
            {isSaving ? "..." : "Сохранить"}
          </Button>
          <Button size="sm" variant="outline" onClick={onClose}>
            Отмена
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="ml-auto"
            onClick={() => onDelete(slot.id)}
          >
            Удалить
          </Button>
        </div>
      </div>
    </div>
  )
}
