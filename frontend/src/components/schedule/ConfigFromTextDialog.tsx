import { useState } from "react"
import { Button } from "../ui/button"
import type { ScheduleConfigFromTextResponse, ScheduleConfigParsedDay } from "../../lib/api-client"

interface ConfigFromTextDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (text: string) => void
  onAccept: () => void
  isParsing: boolean
  parseResult: ScheduleConfigFromTextResponse | null
}

const FORMAT_LABELS: Record<string, string> = {
  presentation_15min: "Презентации (15 мин)",
  poster_60min: "Постерная сессия (60 мин)",
  business: "Бизнес-партнёры",
  roasting: "Прожарка",
}

const TRACK_FILTER_LABELS: Record<string, string> = {
  all_except_research: "Все кроме научного",
  research_only: "Только научный трек",
  business: "Бизнес-секция",
  roasting: "Прожарка",
}

function PreviewDay({ day }: { day: ScheduleConfigParsedDay }) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold">{day.date_hint}</h4>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-muted-foreground">Время:</span>
        <span>{day.start_time} – {day.end_time}</span>
        <span className="text-muted-foreground">Слот:</span>
        <span>{day.slot_duration_minutes} мин</span>
        <span className="text-muted-foreground">Формат:</span>
        <span>{FORMAT_LABELS[day.format] || day.format}</span>
        {day.track_filter && (
          <>
            <span className="text-muted-foreground">Треки:</span>
            <span>{TRACK_FILTER_LABELS[day.track_filter] || day.track_filter}</span>
          </>
        )}
      </div>
      {day.ceremonies.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Церемонии:</p>
          {day.ceremonies.map((c, i) => (
            <div key={i} className="text-xs">{c.label}: {c.start_time}–{c.end_time}</div>
          ))}
        </div>
      )}
      {day.breaks.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Перерывы:</p>
          {day.breaks.map((b, i) => (
            <div key={i} className="text-xs">{b.label}: {b.start_time}–{b.end_time}</div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ConfigFromTextDialog({
  open,
  onClose,
  onSubmit,
  onAccept,
  isParsing,
  parseResult,
}: ConfigFromTextDialogProps) {
  const [text, setText] = useState("")

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-lg border shadow-lg p-6 w-full max-w-lg space-y-4 max-h-[80vh] overflow-y-auto">
        <h3 className="text-lg font-semibold">AI-конфигурация расписания</h3>
        <p className="text-sm text-muted-foreground">
          Опишите временные рамки Demo Day. Залы уже созданы из кластеризации — здесь вы задаёте когда начинаем, перерывы, церемонии.
        </p>

        {!parseResult ? (
          <>
            <textarea
              className="w-full rounded-md border px-3 py-2 text-sm min-h-[120px] resize-y"
              placeholder={"Начинаем в 10, приветственное слово 30 минут, потом защиты.\nОбед 12:30–13:00. Все треки кроме научного.\n\nДень 2 — с 14:00, бизнес-партнёры + прожарка."}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div className="flex gap-2">
              <Button onClick={() => onSubmit(text)} disabled={isParsing || !text.trim()}>
                {isParsing ? "Анализ..." : "Настроить"}
              </Button>
              <Button variant="outline" onClick={onClose}>
                Отмена
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="rounded border p-3 space-y-3 bg-gray-50">
              <p className="text-sm font-medium">Вот что я понял:</p>
              {parseResult.parsed_config.map((day, i) => (
                <PreviewDay key={i} day={day} />
              ))}
              <p className="text-xs text-muted-foreground mt-2">{parseResult.message}</p>
            </div>
            <div className="flex gap-2">
              <Button onClick={onAccept}>
                Принять и сгенерировать
              </Button>
              <Button variant="outline" onClick={() => {
                onClose()
              }}>
                Подправить
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
