import { useState, useEffect, useCallback } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import {
  getCurrentEvent,
  createEvent,
  updateCurrentEvent,
  isNoEventError,
  type Event as EventType,
  type EventCreateRequest,
} from "../lib/api-client"

export function Event() {
  const queryClient = useQueryClient()

  useEffect(() => {
    document.title = `${APP_NAME} - Мероприятие`
  }, [])

  const { data: currentEvent } = useQuery({
    queryKey: ["currentEvent"],
    queryFn: getCurrentEvent,
    retry: (failureCount, error) => {
      if (isNoEventError(error)) return false
      return failureCount < 2
    },
  })

  const handleEventChange = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["currentEvent"] })
    queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
  }, [queryClient])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Мероприятие</h2>
      <EventForm event={currentEvent ?? null} onEventChange={handleEventChange} />
    </div>
  )
}

function EventForm({ event, onEventChange }: { event: EventType | null; onEventChange: () => void }) {
  const [name, setName] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const isEdit = !!event

  useEffect(() => {
    if (event) {
      setName(event.name || "")
      setStartDate(event.start_date || "")
      setEndDate(event.end_date || "")
      setDescription(event.description || "")
    }
  }, [event])

  const createMutation = useMutation({
    mutationFn: (body: EventCreateRequest) => createEvent(body),
    onSuccess: () => {
      setSuccess("Мероприятие создано")
      setError(null)
      onEventChange()
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setSuccess(null)
      const detail = err.response?.data?.detail
      setError(typeof detail === "string" ? detail : err.message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (body: Partial<{ name: string; start_date: string; end_date: string; description: string }>) =>
      updateCurrentEvent(body),
    onSuccess: () => {
      setSuccess("Изменения сохранены")
      setError(null)
      onEventChange()
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setSuccess(null)
      const detail = err.response?.data?.detail
      setError(typeof detail === "string" ? detail : err.message)
    },
  })

  const handleSubmit = () => {
    setError(null)
    setSuccess(null)

    if (!name.trim()) {
      setError("Введите название мероприятия")
      return
    }
    if (!startDate) {
      setError("Введите дату начала")
      return
    }
    if (!endDate) {
      setError("Введите дату окончания")
      return
    }
    if (endDate < startDate) {
      setError("Дата окончания не может быть раньше даты начала")
      return
    }

    if (isEdit) {
      updateMutation.mutate({ name, start_date: startDate, end_date: endDate, description: description || undefined })
    } else {
      createMutation.mutate({ name, start_date: startDate, end_date: endDate, description: description || undefined })
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Редактирование мероприятия" : "Создание мероприятия"}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="event-name">Название</Label>
          <Input
            id="event-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Demo Day 2026"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="event-start">Дата начала</Label>
            <Input
              id="event-start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="event-end">Дата окончания</Label>
            <Input
              id="event-end"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="event-desc">Описание</Label>
          <Input
            id="event-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Описание (необязательно)"
          />
        </div>

        <Button onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Сохранение..." : isEdit ? "Сохранить" : "Создать"}
        </Button>

        {error && <p className="text-sm text-red-500">{error}</p>}
        {success && <p className="text-sm text-green-600">{success}</p>}
      </CardContent>
    </Card>
  )
}
