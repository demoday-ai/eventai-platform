import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Label } from "../components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { APP_NAME } from "../lib/constants"
import {
  getCoverage,
  previewMessaging,
  sendMessaging,
  type MessagingPreviewResponse,
  type MessagingSendResult,
} from "../lib/api-client"

const ROLE_OPTIONS = [
  { code: "student", label: "Студенты" },
  { code: "expert", label: "Эксперты" },
  { code: "guest", label: "Гости" },
  { code: "business", label: "Бизнес-партнёры" },
]

const GUEST_SUBTYPES = [
  { value: "investor", label: "Инвесторы" },
  { value: "business_partner", label: "Бизнес-партнёры" },
  { value: "mentor", label: "Менторы" },
  { value: "hr", label: "HR" },
  { value: "jury", label: "Жюри" },
  { value: "student", label: "Студенты" },
  { value: "applicant", label: "Абитуриенты" },
  { value: "other", label: "Другое" },
]

export function Messaging() {
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [guestSubtype, setGuestSubtype] = useState<string>("")
  const [roomId, setRoomId] = useState<string>("")
  const [template, setTemplate] = useState("")
  const [preview, setPreview] = useState<MessagingPreviewResponse | null>(null)
  const [sendResult, setSendResult] = useState<MessagingSendResult | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Рассылка`
  }, [])

  const { data: rooms } = useQuery({
    queryKey: ["coverage"],
    queryFn: getCoverage,
    enabled: selectedRoles.includes("expert"),
  })

  const previewMutation = useMutation({
    mutationFn: previewMessaging,
    onSuccess: (data) => {
      setPreview(data)
      setSendResult(null)
    },
  })

  const sendMutation = useMutation({
    mutationFn: sendMessaging,
    onSuccess: (data) => {
      setSendResult(data)
    },
  })

  const toggleRole = (code: string) => {
    setSelectedRoles((prev) =>
      prev.includes(code) ? prev.filter((r) => r !== code) : [...prev, code]
    )
    setPreview(null)
    setSendResult(null)
  }

  const canPreview = selectedRoles.length > 0 && template.trim().length > 0

  const handlePreview = () => {
    previewMutation.mutate({
      template,
      roles: selectedRoles,
      guest_subtype: selectedRoles.includes("guest") && guestSubtype ? guestSubtype : null,
      room_id: selectedRoles.includes("expert") && roomId ? roomId : null,
    })
  }

  const handleSend = () => {
    sendMutation.mutate({
      template,
      roles: selectedRoles,
      guest_subtype: selectedRoles.includes("guest") && guestSubtype ? guestSubtype : null,
      room_id: selectedRoles.includes("expert") && roomId ? roomId : null,
    })
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Рассылка сообщений</h2>

      {/* Audience card */}
      <Card>
        <CardHeader>
          <CardTitle>Аудитория</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            {ROLE_OPTIONS.map((role) => (
              <label key={role.code} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedRoles.includes(role.code)}
                  onChange={() => toggleRole(role.code)}
                  className="rounded"
                />
                {role.label}
              </label>
            ))}
          </div>

          {selectedRoles.includes("guest") && (
            <div className="space-y-2">
              <Label htmlFor="guest-subtype">Подтип гостей</Label>
              <Select value={guestSubtype} onValueChange={setGuestSubtype}>
                <SelectTrigger id="guest-subtype">
                  <SelectValue placeholder="Все подтипы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все подтипы</SelectItem>
                  {GUEST_SUBTYPES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {selectedRoles.includes("expert") && rooms && (
            <div className="space-y-2">
              <Label htmlFor="room-filter">Зал</Label>
              <Select value={roomId} onValueChange={setRoomId}>
                <SelectTrigger id="room-filter">
                  <SelectValue placeholder="Все залы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все залы</SelectItem>
                  {rooms.map((room) => (
                    <SelectItem key={room.room_id} value={room.room_id}>
                      {room.room_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Message card */}
      <Card>
        <CardHeader>
          <CardTitle>Сообщение</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="template">Текст сообщения</Label>
            <textarea
              id="template"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Здравствуйте, {name}! ..."
              value={template}
              onChange={(e) => {
                setTemplate(e.target.value)
                setPreview(null)
                setSendResult(null)
              }}
            />
            <p className="text-xs text-muted-foreground">
              Используйте {"{name}"} для подстановки имени получателя.
            </p>
          </div>
          <Button
            onClick={handlePreview}
            disabled={!canPreview || previewMutation.isPending}
          >
            {previewMutation.isPending ? "Загрузка..." : "Предпросмотр"}
          </Button>
          {previewMutation.isError && (
            <p className="text-sm text-red-500">
              Ошибка: {previewMutation.error instanceof Error ? previewMutation.error.message : "Неизвестная ошибка"}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Preview card */}
      {preview && !sendResult && (
        <Card>
          <CardHeader>
            <CardTitle>Предпросмотр</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm">
              <p className="text-muted-foreground">Получателей</p>
              <p className="text-2xl font-bold">{preview.recipient_count}</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Пример сообщения:</p>
              <div className="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
                {preview.sample_message}
              </div>
            </div>
            {preview.recipients_preview.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Получатели (первые {preview.recipients_preview.length}):</p>
                <ul className="text-sm space-y-1">
                  {preview.recipients_preview.map((r) => (
                    <li key={r.user_id} className="text-muted-foreground">
                      {r.full_name} ({r.role}{r.guest_subtype ? `, ${r.guest_subtype}` : ""})
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <Button
              onClick={handleSend}
              disabled={sendMutation.isPending || preview.recipient_count === 0}
            >
              {sendMutation.isPending ? "Отправка..." : `Отправить (${preview.recipient_count})`}
            </Button>
            {sendMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка отправки: {sendMutation.error instanceof Error ? sendMutation.error.message : "Неизвестная ошибка"}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Result card */}
      {sendResult && (
        <Card className="border-green-300">
          <CardHeader>
            <CardTitle>Результат рассылки</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
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
