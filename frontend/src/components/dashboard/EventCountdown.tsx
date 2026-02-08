import { useNavigate } from "react-router-dom"
import { Calendar, Pencil } from "lucide-react"
import { Button } from "../ui/button"
import type { EventSummary } from "../../lib/api-client"

interface EventCountdownProps {
  event: EventSummary
}

function formatDaysUntil(days: number): string {
  if (days === 0) return "сегодня"
  if (days < 0) {
    const absDays = Math.abs(days)
    return `${absDays} ${pluralizeDays(absDays)} назад`
  }
  return `через ${days} ${pluralizeDays(days)}`
}

function pluralizeDays(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "день"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "дня"
  return "дней"
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00")
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

export function EventCountdown({ event }: EventCountdownProps) {
  const navigate = useNavigate()

  return (
    <div className="flex items-center gap-3 text-sm">
      <Calendar className="w-4 h-4 text-muted-foreground shrink-0" />
      <span className="font-medium">{event.name}</span>
      <span className="text-muted-foreground">
        {formatDate(event.start_date)} — {formatDaysUntil(event.days_until)}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        onClick={() => navigate("/import")}
        title="Редактировать событие"
      >
        <Pencil className="w-3.5 h-3.5" />
      </Button>
    </div>
  )
}
