import { useDroppable } from "@dnd-kit/core"
import { cn } from "../../lib/utils"
import { TimelineSlot } from "./TimelineSlot"
import type { RoomSchedule, ScheduleSlotResponse } from "../../lib/api-client"

interface ScheduleTimelineProps {
  rooms: RoomSchedule[]
  dayDate: string
  scaleMinutes: number
  onSlotClick: (slot: ScheduleSlotResponse) => void
}

/** Compute the [dayStart, dayEnd] from slots or default 10:00..19:30 */
function computeTimeRange(rooms: RoomSchedule[], dayDate: string): [Date, Date] {
  let earliest = new Date(`${dayDate}T10:00:00`)
  let latest = new Date(`${dayDate}T19:30:00`)

  for (const room of rooms) {
    for (const slot of room.slots) {
      const s = new Date(slot.start_time)
      const e = new Date(slot.end_time)
      if (s < earliest) earliest = s
      if (e > latest) latest = e
    }
  }

  // Align to 15-min boundaries
  earliest.setMinutes(Math.floor(earliest.getMinutes() / 15) * 15, 0, 0)
  latest.setMinutes(Math.ceil(latest.getMinutes() / 15) * 15, 0, 0)

  return [earliest, latest]
}

function generateTimeLabels(start: Date, end: Date, scaleMinutes: number): string[] {
  const labels: string[] = []
  const cur = new Date(start)
  while (cur < end) {
    labels.push(
      cur.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    )
    cur.setMinutes(cur.getMinutes() + scaleMinutes)
  }
  return labels
}

function getSlotGridPosition(
  slot: ScheduleSlotResponse,
  dayStart: Date,
  scaleMinutes: number
): { rowStart: number; rowSpan: number } {
  const startMs = new Date(slot.start_time).getTime() - dayStart.getTime()
  const endMs = new Date(slot.end_time).getTime() - dayStart.getTime()
  const rowStart = Math.round(startMs / (scaleMinutes * 60 * 1000)) + 2 // +2 for header row (1-indexed)
  const rowSpan = Math.max(1, Math.round((endMs - startMs) / (scaleMinutes * 60 * 1000)))
  return { rowStart, rowSpan }
}

interface DroppableCellProps {
  id: string
  row: number
  col: number
  children?: React.ReactNode
}

function DroppableCell({ id, row, col, children }: DroppableCellProps) {
  const { setNodeRef, isOver } = useDroppable({ id, data: { row, col } })
  return (
    <div
      ref={setNodeRef}
      style={{ gridRow: row, gridColumn: col + 1 }}
      className={cn(
        "border-b border-r border-gray-100 min-h-[2rem]",
        isOver && "bg-blue-50"
      )}
    >
      {children}
    </div>
  )
}

export function ScheduleTimeline({
  rooms,
  dayDate,
  scaleMinutes,
  onSlotClick,
}: ScheduleTimelineProps) {
  const [dayStart, dayEnd] = computeTimeRange(rooms, dayDate)
  const timeLabels = generateTimeLabels(dayStart, dayEnd, scaleMinutes)
  const totalRows = timeLabels.length
  const roomCount = rooms.length

  return (
    <div className="overflow-auto border rounded-lg bg-white" style={{ maxHeight: "70vh" }}>
      <div
        className="grid"
        style={{
          gridTemplateColumns: `60px repeat(${roomCount}, minmax(140px, 1fr))`,
          gridTemplateRows: `auto repeat(${totalRows}, minmax(2rem, auto))`,
        }}
      >
        {/* Corner cell */}
        <div className="sticky top-0 left-0 z-30 bg-gray-50 border-b border-r p-1 text-xs font-medium text-muted-foreground" style={{ gridRow: 1, gridColumn: 1 }}>
          Время
        </div>

        {/* Room headers (sticky top) */}
        {rooms.map((room, idx) => (
          <div
            key={room.room_id}
            className="sticky top-0 z-20 bg-gray-50 border-b border-r p-1.5 text-xs font-medium truncate text-center"
            style={{ gridRow: 1, gridColumn: idx + 2 }}
            title={room.room_name}
          >
            {room.room_name}
          </div>
        ))}

        {/* Time labels (sticky left) */}
        {timeLabels.map((label, rowIdx) => (
          <div
            key={`time-${rowIdx}`}
            className="sticky left-0 z-10 bg-gray-50 border-b border-r px-1 text-[10px] text-muted-foreground flex items-start pt-0.5"
            style={{ gridRow: rowIdx + 2, gridColumn: 1 }}
          >
            {label}
          </div>
        ))}

        {/* Droppable grid cells */}
        {timeLabels.map((_, rowIdx) =>
          rooms.map((_, colIdx) => (
            <DroppableCell
              key={`cell-${rowIdx}-${colIdx}`}
              id={`cell-${rowIdx}-${colIdx}`}
              row={rowIdx + 2}
              col={colIdx + 1}
            />
          ))
        )}

        {/* Slots */}
        {rooms.map((room, colIdx) =>
          room.slots.map((slot) => {
            const { rowStart, rowSpan } = getSlotGridPosition(slot, dayStart, scaleMinutes)
            return (
              <TimelineSlot
                key={slot.id}
                slot={slot}
                rowStart={rowStart}
                rowSpan={rowSpan}
                column={colIdx + 1}
                onClick={onSlotClick}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
