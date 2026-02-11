import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Check, Pencil, X } from "lucide-react"
import { getProjectDetail, updateProject, getTags, isNoEventError } from "../lib/api-client"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { APP_NAME } from "../lib/constants"

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const [editingTitle, setEditingTitle] = useState(false)
  const [editingDescription, setEditingDescription] = useState(false)
  const [editingTags, setEditingTags] = useState(false)

  const [titleDraft, setTitleDraft] = useState("")
  const [descriptionDraft, setDescriptionDraft] = useState("")
  const [tagsDraft, setTagsDraft] = useState("")

  useEffect(() => {
    document.title = `${APP_NAME} - Проект`
  }, [])

  const { data: project, isLoading, error } = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProjectDetail(id!),
    enabled: !!id,
  })

  const { data: tagsData } = useQuery({
    queryKey: ["tags"],
    queryFn: getTags,
  })

  const updateMutation = useMutation({
    mutationFn: (body: { title?: string; description?: string; tags?: string[] }) =>
      updateProject(id!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] })
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      setEditingTitle(false)
      setEditingDescription(false)
      setEditingTags(false)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Загрузка...</p>
      </div>
    )
  }

  if (error) {
    const msg = isNoEventError(error) ? "Нет активного мероприятия" : "Проект не найден"
    return (
      <div className="flex items-center justify-center py-16">
        <Card className="border-red-500">
          <CardContent className="pt-6">
            <p className="text-red-500">{msg}</p>
            <Link to="/projects">
              <Button variant="link" className="mt-2 px-0">Назад к проектам</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!project) return null

  const availableTags = tagsData?.tags || []

  const startEditTitle = () => {
    setTitleDraft(project.title)
    setEditingTitle(true)
  }

  const saveTitle = () => {
    if (titleDraft.trim() && titleDraft !== project.title) {
      updateMutation.mutate({ title: titleDraft.trim() })
    } else {
      setEditingTitle(false)
    }
  }

  const startEditDescription = () => {
    setDescriptionDraft(project.description)
    setEditingDescription(true)
  }

  const saveDescription = () => {
    if (descriptionDraft !== project.description) {
      updateMutation.mutate({ description: descriptionDraft })
    } else {
      setEditingDescription(false)
    }
  }

  const startEditTags = () => {
    setTagsDraft(project.tags.join(", "))
    setEditingTags(true)
  }

  const saveTags = () => {
    const newTags = tagsDraft
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
    updateMutation.mutate({ tags: newTags })
  }

  const addTag = (tag: string) => {
    const current = tagsDraft
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
    if (!current.includes(tag)) {
      setTagsDraft([...current, tag].join(", "))
    }
  }

  const removeTag = (tag: string) => {
    const newTags = project.tags.filter((t) => t !== tag)
    updateMutation.mutate({ tags: newTags })
  }

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString)
      return date.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-3">
        <Link to="/projects">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Назад
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            {editingTitle ? (
              <div className="flex items-center gap-2 flex-1">
                <Input
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  className="text-lg font-semibold"
                  onKeyDown={(e) => { if (e.key === "Enter") saveTitle() }}
                />
                <Button size="sm" variant="ghost" onClick={saveTitle} disabled={updateMutation.isPending}>
                  <Check className="h-4 w-4" />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingTitle(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <CardTitle className="text-xl">{project.title}</CardTitle>
                <Button size="sm" variant="ghost" onClick={startEditTitle}>
                  <Pencil className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Description */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm font-medium text-muted-foreground">Описание</h3>
              {!editingDescription && (
                <Button size="sm" variant="ghost" onClick={startEditDescription}>
                  <Pencil className="h-3 w-3" />
                </Button>
              )}
            </div>
            {editingDescription ? (
              <div className="space-y-2">
                <textarea
                  className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={descriptionDraft}
                  onChange={(e) => setDescriptionDraft(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={saveDescription} disabled={updateMutation.isPending}>
                    Сохранить
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingDescription(false)}>
                    Отмена
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm whitespace-pre-wrap">{project.description}</p>
            )}
          </div>

          {/* Tags */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm font-medium text-muted-foreground">Теги</h3>
              {!editingTags && (
                <Button size="sm" variant="ghost" onClick={startEditTags}>
                  <Pencil className="h-3 w-3" />
                </Button>
              )}
            </div>
            {editingTags ? (
              <div className="space-y-3">
                <Input
                  value={tagsDraft}
                  onChange={(e) => setTagsDraft(e.target.value)}
                  placeholder="Введите теги через запятую"
                />
                {availableTags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {availableTags.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => addTag(tag)}
                        className="px-2 py-0.5 text-xs bg-muted rounded hover:bg-muted/80"
                      >
                        + {tag}
                      </button>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <Button size="sm" onClick={saveTags} disabled={updateMutation.isPending}>
                    Сохранить
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingTags(false)}>
                    Отмена
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {project.tags.length > 0 ? (
                  project.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-xs rounded"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTag(tag)}
                        className="hover:text-red-500"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">Нет тегов</span>
                )}
              </div>
            )}
          </div>

          {/* Info grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Автор</h3>
              <p className="text-sm">{project.author}</p>
            </div>
            {project.telegram_contact && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Телеграм</h3>
                <p className="text-sm">@{project.telegram_contact}</p>
              </div>
            )}
            {project.track && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Трек</h3>
                <p className="text-sm">{project.track}</p>
              </div>
            )}
            {project.room_name && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Зал</h3>
                <p className="text-sm">{project.room_name}</p>
              </div>
            )}
            {project.start_time && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Время</h3>
                <p className="text-sm">
                  {formatTime(project.start_time)} — {project.end_time && formatTime(project.end_time)}
                </p>
              </div>
            )}
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Статус</h3>
              <p className="text-sm">
                {project.status === "confirmed" ? "Подтверждён" : project.status === "pending" ? "Не распределён" : "Отменён"}
              </p>
            </div>
          </div>

          {/* Links */}
          {(project.github_url || project.presentation_url || project.demo_url) && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Ссылки</h3>
              <div className="flex flex-wrap gap-3">
                {project.github_url && (
                  <a href={project.github_url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    GitHub
                  </a>
                )}
                {project.presentation_url && (
                  <a href={project.presentation_url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    Презентация
                  </a>
                )}
                {project.demo_url && (
                  <a href={project.demo_url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    Демо
                  </a>
                )}
              </div>
            </div>
          )}

          {project.tech_stack && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Технологии</h3>
              <p className="text-sm">{project.tech_stack}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
