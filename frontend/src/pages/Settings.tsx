import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import { getCurrentEvent, updateCurrentEvent, type Event, type EventUpdateRequest } from "../lib/api-client"

export function Settings() {
  const queryClient = useQueryClient()

  useEffect(() => {
    document.title = `${APP_NAME} - Настройки`
  }, [])

  const { data: event, isLoading, error } = useQuery<Event>({
    queryKey: ["currentEvent"],
    queryFn: getCurrentEvent,
  })

  const [name, setName] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [description, setDescription] = useState("")
  const [dateError, setDateError] = useState("")

  // Populate form when data loads
  useEffect(() => {
    if (event) {
      setName(event.name || "")
      setStartDate(event.start_date || "")
      setEndDate(event.end_date || "")
      setDescription(event.description || "")
    }
  }, [event])

  const mutation = useMutation({
    mutationFn: (body: EventUpdateRequest) => updateCurrentEvent(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentEvent"] })
    },
  })

  const validate = (): boolean => {
    if (startDate && endDate && endDate < startDate) {
      setDateError("Дата окончания должна быть не раньше даты начала")
      return false
    }
    setDateError("")
    return true
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    const body: EventUpdateRequest = {}
    if (name !== (event?.name || "")) body.name = name
    if (startDate !== (event?.start_date || "")) body.start_date = startDate
    if (endDate !== (event?.end_date || "")) body.end_date = endDate
    if (description !== (event?.description || "")) body.description = description

    mutation.mutate(body)
  }

  if (isLoading) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Настройки</h2>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Загрузка...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Настройки</h2>
        <Card className="border-red-500">
          <CardContent className="pt-6">
            <p className="text-red-500">
              Ошибка загрузки: {error instanceof Error ? error.message : "Неизвестная ошибка"}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Настройки</h2>

      <Card>
        <CardHeader>
          <CardTitle>Мероприятие</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="event-name">Название</Label>
              <Input
                id="event-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start-date">Дата начала</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value)
                    setDateError("")
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end-date">Дата окончания</Label>
                <Input
                  id="end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value)
                    setDateError("")
                  }}
                />
              </div>
            </div>

            {dateError && (
              <p className="text-sm text-red-500">{dateError}</p>
            )}

            <div className="space-y-2">
              <Label htmlFor="description">Описание</Label>
              <textarea
                id="description"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Сохранение..." : "Сохранить"}
              </Button>

              {mutation.isSuccess && (
                <span className="text-sm text-green-600">Сохранено</span>
              )}
              {mutation.isError && (
                <span className="text-sm text-red-500">
                  Ошибка: {mutation.error instanceof Error ? mutation.error.message : "Не удалось сохранить"}
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
