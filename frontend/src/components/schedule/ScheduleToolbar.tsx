import { Button } from "../ui/button"
import {
  Play,
  Coffee,
  Layers,
  Download,
  Sparkles,
} from "lucide-react"

interface ScheduleToolbarProps {
  onAutoFill: () => void
  onAddBreak: () => void
  onAddSection: () => void
  onExportICS: () => void
  onConfigFromText: () => void
  isGenerating: boolean
  scaleMinutes: number
  onScaleChange: (scale: number) => void
}

export function ScheduleToolbar({
  onAutoFill,
  onAddBreak,
  onAddSection,
  onExportICS,
  onConfigFromText,
  isGenerating,
  scaleMinutes,
  onScaleChange,
}: ScheduleToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" onClick={onAutoFill} disabled={isGenerating}>
        <Play className="h-3.5 w-3.5 mr-1" />
        {isGenerating ? "Генерация..." : "Авто-заполнить"}
      </Button>
      <Button size="sm" variant="outline" onClick={onConfigFromText}>
        <Sparkles className="h-3.5 w-3.5 mr-1" />
        AI-конфигурация
      </Button>
      <Button size="sm" variant="outline" onClick={onAddBreak}>
        <Coffee className="h-3.5 w-3.5 mr-1" />
        + Перерыв
      </Button>
      <Button size="sm" variant="outline" onClick={onAddSection}>
        <Layers className="h-3.5 w-3.5 mr-1" />
        + Секция
      </Button>

      <div className="ml-auto flex items-center gap-2">
        <select
          className="rounded border px-2 py-1 text-xs"
          value={scaleMinutes}
          onChange={(e) => onScaleChange(Number(e.target.value))}
          aria-label="Масштаб"
        >
          <option value={5}>5 мин</option>
          <option value={10}>10 мин</option>
          <option value={15}>15 мин</option>
          <option value={30}>30 мин</option>
        </select>
        <Button size="sm" variant="outline" onClick={onExportICS}>
          <Download className="h-3.5 w-3.5 mr-1" />
          .ics
        </Button>
      </div>
    </div>
  )
}
