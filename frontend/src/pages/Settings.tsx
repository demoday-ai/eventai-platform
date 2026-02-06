import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import {
  getCurrentEvent, updateCurrentEvent, getAuditLog,
  getOrganizers, addOrganizer, removeOrganizer,
  getTags, addTags, suggestTags, replaceTags, deleteTag,
  type Event, type EventUpdateRequest, type AuditLogItem,
  type OrganizerItem,
} from "../lib/api-client"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"

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

      <TagsSection />

      <OrganizersSection />

      <AuditLogSection />
    </div>
  )
}

function TagsSection() {
  const queryClient = useQueryClient()
  const [tagInput, setTagInput] = useState("")
  const [tagError, setTagError] = useState("")
  const [tagInfo, setTagInfo] = useState<string | null>(null)

  // Suggest flow state
  const [suggestedTags, setSuggestedTags] = useState<string[]>([])
  const [selectedSuggested, setSelectedSuggested] = useState<Set<string>>(new Set())
  const [showSuggestions, setShowSuggestions] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ["tags"],
    queryFn: getTags,
  })

  const mutation = useMutation({
    mutationFn: (tags: string[]) => addTags(tags),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["tags"] })
      setTagInput("")
      const added = result.added.length
      const skipped = result.skipped.length
      if (added > 0) {
        setTagInfo(`Добавлено: ${added}. Уже были: ${skipped}.`)
      } else {
        setTagInfo(`Новых тегов нет. Уже были: ${skipped}.`)
      }
      setTagError("")
    },
    onError: (err) => {
      setTagError(err instanceof Error ? err.message : "Не удалось добавить теги")
    },
  })

  const suggestMutation = useMutation({
    mutationFn: suggestTags,
    onSuccess: (result) => {
      if (result.suggested_tags.length === 0) {
        setTagError("Нет проектов для анализа или LLM не вернул теги")
        return
      }
      setSuggestedTags(result.suggested_tags)
      setSelectedSuggested(new Set(result.suggested_tags))
      setShowSuggestions(true)
      setTagInfo(`Проанализировано проектов: ${result.project_count}`)
      setTagError("")
    },
    onError: (err) => {
      setTagError(err instanceof Error ? err.message : "Не удалось получить предложения")
    },
  })

  const replaceMutation = useMutation({
    mutationFn: replaceTags,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["tags"] })
      setShowSuggestions(false)
      setSuggestedTags([])
      setSelectedSuggested(new Set())
      const added = result.added.length
      const removed = result.removed.length
      setTagInfo(`Утверждено. Добавлено: ${added}, удалено: ${removed}. Итого тегов: ${result.final_tags.length}.`)
      setTagError("")
    },
    onError: (err) => {
      setTagError(err instanceof Error ? err.message : "Не удалось обновить теги")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (err) => {
      setTagError(err instanceof Error ? err.message : "Не удалось удалить тег")
    },
  })

  const tags = data?.tags ?? []

  const parseTags = (raw: string) => {
    return raw
      .split(/[,\\n]+/g)
      .map((tag) => tag.trim())
      .filter(Boolean)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = parseTags(tagInput)
    if (parsed.length === 0) {
      setTagError("Введите хотя бы один тег")
      return
    }
    setTagInfo(null)
    mutation.mutate(parsed)
  }

  const toggleSuggested = (tag: string) => {
    setSelectedSuggested((prev) => {
      const next = new Set(prev)
      if (next.has(tag)) {
        next.delete(tag)
      } else {
        next.add(tag)
      }
      return next
    })
  }

  const handleApprove = () => {
    const selected = Array.from(selectedSuggested)
    if (selected.length === 0) {
      setTagError("Выберите хотя бы один тег")
      return
    }
    replaceMutation.mutate(selected)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Теги конференции</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Теги помогают в автокластеризации и подборе экспертов. При загрузке проектов применяются только утверждённые теги.
        </p>

        {isLoading && <p className="text-muted-foreground">Загрузка...</p>}
        {error && (
          <p className="text-sm text-red-500">
            Ошибка загрузки: {error instanceof Error ? error.message : "Неизвестная ошибка"}
          </p>
        )}

        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span key={tag} className="inline-flex items-center gap-1 px-3 py-1 bg-muted text-sm rounded-full">
                {tag}
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(tag)}
                  disabled={deleteMutation.isPending}
                  className="ml-0.5 text-muted-foreground hover:text-destructive transition-colors"
                  title="Удалить тег"
                >
                  x
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Теги пока не добавлены.</p>
        )}

        {/* Suggest tags from LLM */}
        {!showSuggestions && (
          <Button
            variant="outline"
            onClick={() => {
              setTagInfo(null)
              setTagError("")
              suggestMutation.mutate()
            }}
            disabled={suggestMutation.isPending}
          >
            {suggestMutation.isPending ? "Анализ проектов..." : "Предложить теги на основе проектов"}
          </Button>
        )}

        {/* Suggestion chips */}
        {showSuggestions && suggestedTags.length > 0 && (
          <div className="border rounded-md p-4 space-y-3">
            <p className="text-sm font-medium">Предложенные теги (нажмите, чтобы убрать/добавить):</p>
            <div className="flex flex-wrap gap-2">
              {suggestedTags.map((tag) => {
                const isSelected = selectedSuggested.has(tag)
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => toggleSuggested(tag)}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      isSelected
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-muted text-muted-foreground border-transparent line-through"
                    }`}
                  >
                    {tag}
                  </button>
                )
              })}
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleApprove}
                disabled={replaceMutation.isPending || selectedSuggested.size === 0}
              >
                {replaceMutation.isPending ? "Сохранение..." : `Утвердить (${selectedSuggested.size})`}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowSuggestions(false)
                  setSuggestedTags([])
                  setSelectedSuggested(new Set())
                }}
              >
                Отмена
              </Button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="tag-input">Добавить теги вручную</Label>
            <textarea
              id="tag-input"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Например: NLP, CV, Финтех"
              value={tagInput}
              onChange={(e) => {
                setTagInput(e.target.value)
                setTagError("")
                setTagInfo(null)
              }}
              disabled={mutation.isPending}
            />
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Добавление..." : "Добавить"}
            </Button>
            {tagInfo && <span className="text-sm text-green-600">{tagInfo}</span>}
            {tagError && <span className="text-sm text-red-500">{tagError}</span>}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function OrganizersSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [username, setUsername] = useState("")
  const [orgName, setOrgName] = useState("")

  const { data: organizers, isLoading } = useQuery<OrganizerItem[]>({
    queryKey: ["organizers"],
    queryFn: getOrganizers,
  })

  const addMutation = useMutation({
    mutationFn: addOrganizer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizers"] })
      setShowForm(false)
      setUsername("")
      setOrgName("")
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeOrganizer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizers"] })
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) return
    addMutation.mutate({
      telegram_id: "",
      telegram_username: username.trim(),
      name: orgName.trim() || null,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Организаторы</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <p className="text-muted-foreground">Загрузка...</p>}

        {organizers && organizers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4">Username</th>
                  <th className="text-left py-2 pr-4">Имя</th>
                  <th className="text-left py-2 pr-4">Добавлен</th>
                  <th className="text-left py-2"></th>
                </tr>
              </thead>
              <tbody>
                {organizers.map((org: OrganizerItem) => (
                  <tr key={org.id} className="border-b">
                    <td className="py-2 pr-4">{org.telegram_username || "—"}</td>
                    <td className="py-2 pr-4">{org.name || "—"}</td>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {new Date(org.created_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td className="py-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => removeMutation.mutate(org.id)}
                        disabled={removeMutation.isPending}
                      >
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {organizers && organizers.length === 0 && (
          <p className="text-muted-foreground">Нет организаторов</p>
        )}

        {!showForm && (
          <Button variant="outline" onClick={() => setShowForm(true)}>
            Добавить организатора
          </Button>
        )}

        {showForm && (
          <form onSubmit={handleAdd} className="space-y-3 border rounded-md p-4">
            <div className="space-y-2">
              <Label htmlFor="org-username">Username *</Label>
              <Input
                id="org-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="@username"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-name">Имя</Label>
              <Input
                id="org-name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Иван Иванов"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button type="submit" disabled={addMutation.isPending || !username.trim()}>
                {addMutation.isPending ? "Добавление..." : "Добавить"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>
                Отмена
              </Button>
            </div>
            {addMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка: {addMutation.error instanceof Error ? addMutation.error.message : "Не удалось добавить"}
              </p>
            )}
          </form>
        )}
      </CardContent>
    </Card>
  )
}

const ACTION_LABELS: Record<string, string> = {
  event_update: "Обновление события",
  upload_projects: "Загрузка проектов",
  upload_experts: "Загрузка экспертов",
  upload_guests: "Загрузка гостей",
  send_briefing: "Отправка брифинга",
  send_messaging: "Отправка рассылки",
  schedule_generate: "Генерация расписания",
  schedule_approve: "Утверждение расписания",
  slot_update: "Изменение слота",
}

function AuditLogSection() {
  const [actionFilter, setActionFilter] = useState("")

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ["auditLog", actionFilter],
    queryFn: () => getAuditLog({ action: actionFilter && actionFilter !== "all" ? actionFilter : undefined, limit: 20 }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Журнал действий</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Label htmlFor="audit-action-filter">Фильтр по действию</Label>
          <Select value={actionFilter} onValueChange={setActionFilter}>
            <SelectTrigger id="audit-action-filter" className="w-[220px]">
              <SelectValue placeholder="Все действия" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все действия</SelectItem>
              {Object.entries(ACTION_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {auditLoading && <p className="text-muted-foreground">Загрузка...</p>}

        {auditData && auditData.items.length === 0 && (
          <p className="text-muted-foreground">Нет записей</p>
        )}

        {auditData && auditData.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4">Время</th>
                  <th className="text-left py-2 pr-4">Пользователь</th>
                  <th className="text-left py-2 pr-4">Действие</th>
                  <th className="text-left py-2">Объект</th>
                </tr>
              </thead>
              <tbody>
                {auditData.items.map((item: AuditLogItem) => (
                  <tr key={item.id} className="border-b">
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString("ru-RU")}
                    </td>
                    <td className="py-2 pr-4">{item.user_name || "—"}</td>
                    <td className="py-2 pr-4">{ACTION_LABELS[item.action] || item.action}</td>
                    <td className="py-2">
                      {item.entity_type || "—"}
                      {item.entity_id ? ` #${item.entity_id.slice(0, 8)}` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
