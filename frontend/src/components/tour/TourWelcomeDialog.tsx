import { GraduationCap, X } from "lucide-react"
import { Button } from "../ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"

interface TourWelcomeDialogProps {
  onStart: () => void
  onSkip: () => void
}

export function TourWelcomeDialog({ onStart, onSkip }: TourWelcomeDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <Card className="max-w-md mx-4 shadow-2xl border-blue-200">
        <CardHeader className="relative pb-4">
          <button
            onClick={onSkip}
            className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <GraduationCap className="w-8 h-8 text-blue-600" />
            </div>
            <CardTitle className="text-xl">Добро пожаловать в EventAI!</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground leading-relaxed">
            Это ваш первый визит. Хотите пройти быструю обучалку? Мы покажем все основные
            функции административной панели за 3 минуты.
          </p>
          <div className="space-y-3 pt-2">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="text-blue-600 mt-0.5">•</span>
                <span>Импорт данных и управление проектами</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 mt-0.5">•</span>
                <span>Кластеризация и распределение экспертов</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 mt-0.5">•</span>
                <span>Расписание и рассылки участникам</span>
              </li>
            </ul>
          </div>
          <div className="flex gap-3 pt-4">
            <Button onClick={onStart} className="flex-1" size="lg">
              Начать обучалку
            </Button>
            <Button onClick={onSkip} variant="outline" className="flex-1" size="lg">
              Позже
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center">
            Вы всегда можете запустить тур заново в разделе Настройки
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
