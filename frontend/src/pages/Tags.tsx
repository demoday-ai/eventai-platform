import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import { getTags, addTags, seedDefaultTags, suggestTags, replaceTags, deleteTag } from "../lib/api-client"

export function Tags() {
  const queryClient = useQueryClient()
  const [tagInput, setTagInput] = useState("")
  const [tagError, setTagError] = useState("")
  const [tagInfo, setTagInfo] = useState<string | null>(null)

  // Suggest flow state
  const [suggestedTags, setSuggestedTags] = useState<string[]>([])
  const [selectedSuggested, setSelectedSuggested] = useState<Set<string>>(new Set())
  const [showSuggestions, setShowSuggestions] = useState(false)

  useEffect(() => {
    document.title = `${APP_NAME} - Теги`
  }, [])

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

  const seedMutation = useMutation({
    mutationFn: seedDefaultTags,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["tags"] })
      const added = result.added.length
      setTagInfo(`Добавлено стандартных тегов: ${added}.`)
      setTagError("")
    },
    onError: (err) => {
      setTagError(err instanceof Error ? err.message : "Не удалось добавить стандартные теги")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTag,
    onMutate: async (tagToDelete) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["tags"] })

      // Snapshot previous value
      const previousTags = queryClient.getQueryData(["tags"])

      // Optimistically update
      queryClient.setQueryData(["tags"], (old: { tags: string[] } | undefined) => {
        if (!old) return old
        return { tags: old.tags.filter((t) => t !== tagToDelete) }
      })

      return { previousTags }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (err, _tagToDelete, context) => {
      // Ignore 404 errors (tag already deleted)
      if (err instanceof Error && err.message.includes("404")) {
        queryClient.invalidateQueries({ queryKey: ["tags"] })
        return
      }

      // Rollback on other errors
      if (context?.previousTags) {
        queryClient.setQueryData(["tags"], context.previousTags)
      }
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
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Теги</h2>

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
                <span key={tag} className="inline-flex items-center justify-between gap-1 px-3 py-1 bg-muted text-sm rounded-full w-32">
                  <span>{tag}</span>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(tag)}
                    disabled={deleteMutation.isPending}
                    className="text-muted-foreground hover:text-destructive transition-colors"
                    title="Удалить тег"
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
          ) : (
            !isLoading && !error && (
              <div className="border rounded-md p-4 space-y-3 text-center">
                <p className="text-sm text-muted-foreground">
                  Теги пока не добавлены. Добавьте стандартный набор или создайте свои.
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setTagInfo(null)
                    setTagError("")
                    seedMutation.mutate()
                  }}
                  disabled={seedMutation.isPending}
                >
                  {seedMutation.isPending ? "Добавление..." : "Добавить стандартные теги"}
                </Button>
              </div>
            )
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
    </div>
  )
}
