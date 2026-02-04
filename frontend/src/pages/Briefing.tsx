import { useState, useEffect } from "react"
import { useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { APP_NAME } from "../lib/constants"
import {
  getBriefingPreview,
  sendBriefing,
  type BriefingPreview as BriefingPreviewType,
  type BriefingSendResult,
} from "../lib/api-client"

export function Briefing() {
  const [preview, setPreview] = useState<BriefingPreviewType | null>(null)
  const [sendResult, setSendResult] = useState<BriefingSendResult | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Брифинг`
  }, [])

  const previewMutation = useMutation({
    mutationFn: getBriefingPreview,
    onSuccess: (data) => {
      setPreview(data)
    },
  })

  const sendMutation = useMutation({
    mutationFn: sendBriefing,
    onSuccess: (data) => {
      setSendResult(data)
    },
  })

  const is404 =
    previewMutation.isError &&
    previewMutation.error instanceof Error &&
    previewMutation.error.message.includes("404")

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Брифинг экспертов</h2>

      {/* Preview button */}
      {!preview && !sendResult && (
        <Card>
          <CardHeader>
            <CardTitle>Брифинг</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Загрузите предпросмотр, чтобы увидеть, сколько экспертов получат брифинг.
            </p>
            <Button
              onClick={() => previewMutation.mutate()}
              disabled={previewMutation.isPending}
            >
              {previewMutation.isPending ? "Загрузка..." : "Предпросмотр"}
            </Button>
            {is404 && (
              <p className="text-sm text-red-500">
                Нет одобренной кластеризации. Сначала одобрите кластеризацию и матчинг.
              </p>
            )}
            {previewMutation.isError && !is404 && (
              <p className="text-sm text-red-500">
                Ошибка: {previewMutation.error instanceof Error ? previewMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Preview card */}
      {preview && !sendResult && (
        <Card>
          <CardHeader>
            <CardTitle>Предпросмотр брифинга</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Всего экспертов</p>
                <p className="text-2xl font-bold">{preview.expert_count}</p>
              </div>
              <div>
                <p className="text-muted-foreground">С Telegram</p>
                <p className="text-2xl font-bold text-green-600">{preview.with_telegram}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Без Telegram</p>
                <p className="text-2xl font-bold text-yellow-600">{preview.without_telegram}</p>
              </div>
            </div>
            <Button
              onClick={() => sendMutation.mutate()}
              disabled={sendMutation.isPending}
            >
              {sendMutation.isPending ? "Отправка..." : "Отправить брифинги"}
            </Button>
            {sendMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка отправки: {sendMutation.error instanceof Error ? sendMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Send result card */}
      {sendResult && (
        <Card className="border-green-300">
          <CardHeader>
            <CardTitle>Брифинги отправлены</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Отправлено</p>
                <p className="text-2xl font-bold text-green-600">{sendResult.sent}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Ошибки</p>
                <p className="text-2xl font-bold text-red-600">{sendResult.failed}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Пропущено</p>
                <p className="text-2xl font-bold text-yellow-600">{sendResult.skipped}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
