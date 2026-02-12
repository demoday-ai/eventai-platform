import { useDraggable } from "@dnd-kit/core"
import { cn } from "../../lib/utils"
import type { ScheduleSlotResponse } from "../../lib/api-client"

interface TimelineSlotProps {
  slot: ScheduleSlotResponse
  rowStart: number
  rowSpan: number
  column: number
  onClick: (slot: ScheduleSlotResponse) => void
}

const SLOT_COLORS: Record<string, string> = {
  project: "bg-blue-100 border-blue-300 text-blue-900 hover:bg-blue-200",
  break: "bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200",
  ceremony: "bg-amber-100 border-amber-300 text-amber-900 hover:bg-amber-200",
  section: "bg-green-100 border-green-300 text-green-900 hover:bg-green-200",
}

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
  } catch {
    return isoString
  }
}

function getSlotLabel(slot: ScheduleSlotResponse): string {
  if (slot.slot_type !== "project" && slot.title) return slot.title
  return slot.project_title || slot.title || ""
}

export function TimelineSlot({ slot, rowStart, rowSpan, column, onClick }: TimelineSlotProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `slot-${slot.id}`,
    data: { type: "timeline-slot", slot },
  })

  const style: React.CSSProperties = {
    gridRow: `${rowStart} / span ${rowSpan}`,
    gridColumn: column + 1, // +1 because column 1 is time labels
    ...(transform ? { transform: `translate(${transform.x}px, ${transform.y}px)` } : {}),
    zIndex: isDragging ? 50 : undefined,
  }

  const colorClass = SLOT_COLORS[slot.slot_type] || SLOT_COLORS.project

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "mx-0.5 overflow-hidden rounded border px-1.5 py-0.5 text-xs cursor-grab select-none",
        colorClass,
        isDragging && "opacity-50 shadow-lg",
        slot.status === "cancelled" && "opacity-40 line-through"
      )}
      onClick={() => onClick(slot)}
      {...listeners}
      {...attributes}
      title={`${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}\n${getSlotLabel(slot)}${slot.project_author ? `\n${slot.project_author}` : ""}`}
    >
      <div className="truncate font-medium">{getSlotLabel(slot)}</div>
      {slot.slot_type === "project" && slot.project_author && rowSpan > 1 && (
        <div className="truncate text-[10px] opacity-70">{slot.project_author}</div>
      )}
    </div>
  )
}
