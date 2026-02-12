import { Tabs, TabsList, TabsTrigger } from "../ui/tabs"
import type { DaySchedule } from "../../lib/api-client"

interface DayTabsProps {
  days: DaySchedule[]
  selectedDay: string
  onDayChange: (day: string) => void
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("ru-RU", {
      weekday: "short",
      day: "numeric",
      month: "long",
    })
  } catch {
    return dateStr
  }
}

export function DayTabs({ days, selectedDay, onDayChange }: DayTabsProps) {
  if (days.length === 0) return null

  return (
    <Tabs value={selectedDay} onValueChange={onDayChange}>
      <TabsList>
        {days.map((day) => {
          const slotCount = day.rooms.reduce((s, r) => s + r.slots.length, 0)
          return (
            <TabsTrigger key={day.date} value={day.date}>
              {formatDate(day.date)}
              <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium">
                {slotCount}
              </span>
            </TabsTrigger>
          )
        })}
      </TabsList>
    </Tabs>
  )
}
