import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { FolderOpen, Sparkles } from "lucide-react"
import { getProjects, getCoverage, generateProjectTags, getTagGenerationStatus, isNoEventError, type ProjectListItem } from "../lib/api-client"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { Label } from "../components/ui/label"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"

export function ProjectsList() {
  const queryClient = useQueryClient()
  const [roomFilter, setRoomFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [generateInfo, setGenerateInfo] = useState<string | null>(null)
  const [tagTaskId, setTagTaskId] = useState<string | null>(null)
  const [tagProgress, setTagProgress] = useState<{ current: number; total: number; status: string } | null>(null)

  // Set page title
  useEffect(() => {
    document.title = `${APP_NAME} - Проекты`
  }, [])

  const generateMutation = useMutation({
    mutationFn: generateProjectTags,
    onSuccess: (result) => {
      if (result.task_id) {
        setTagTaskId(result.task_id)
        setTagProgress({ current: 0, total: 0, status: "running" })
      } else {
        queryClient.invalidateQueries({ queryKey: ["projects"] })
        if (result.message) {
          setGenerateInfo(result.message)
        } else {
          setGenerateInfo(`Обработано: ${result.processed}, теги присвоены: ${result.tagged}`)
        }
        setTimeout(() => setGenerateInfo(null), 5000)
      }
    },
    onError: (err) => {
      setGenerateInfo(err instanceof Error ? err.message : "Ошибка генерации тегов")
      setTimeout(() => setGenerateInfo(null), 5000)
    },
  })

  // Poll tag generation progress
  useEffect(() => {
    if (!tagTaskId) return

    const interval = setInterval(async () => {
      try {
        const status = await getTagGenerationStatus(tagTaskId)
        setTagProgress({ current: status.current, total: status.total, status: status.status })

        if (status.status === "completed") {
          setTagTaskId(null)
          setTagProgress(null)
          queryClient.invalidateQueries({ queryKey: ["projects"] })
          setGenerateInfo(`Обработано: ${status.processed}, теги присвоены: ${status.tagged}`)
          setTimeout(() => setGenerateInfo(null), 5000)
        } else if (status.status === "failed") {
          setTagTaskId(null)
          setTagProgress(null)
          setGenerateInfo(status.error || "Ошибка генерации тегов")
          setTimeout(() => setGenerateInfo(null), 5000)
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [tagTaskId, queryClient])

  // Build query params
  const params = {
    ...(roomFilter && { room_id: roomFilter }),
    ...(statusFilter && { status: statusFilter }),
    ...(searchQuery && { search: searchQuery }),
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ["projects", params],
    queryFn: () => getProjects(params),
    refetchInterval: 60000,
  })

  // Get rooms for filter
  const { data: coverageData } = useQuery({
    queryKey: ["coverage"],
    queryFn: getCoverage,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Загрузка...</p>
      </div>
    )
  }

  if (error && isNoEventError(error)) {
    return (
      <PageEmptyState
        icon={FolderOpen}
        title="Проекты ещё не загружены"
        description="Загрузите проекты на странице Импорта, чтобы создать мероприятие."
        actionLabel="Перейти к импорту"
        actionLink="/import"
      />
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-16">
        <Card className="border-red-500">
          <CardContent className="pt-6">
            <p className="text-red-500">
              Ошибка загрузки данных: {error instanceof Error ? error.message : "Неизвестная ошибка"}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const projects = data || []

  const getStatusColor = (status: ProjectListItem["status"]) => {
    switch (status) {
      case "confirmed":
        return "text-green-600 bg-green-50"
      case "pending":
        return "text-yellow-600 bg-yellow-50"
      case "cancelled":
        return "text-red-600 bg-red-50"
    }
  }

  const getStatusText = (status: ProjectListItem["status"]) => {
    switch (status) {
      case "confirmed":
        return "Подтверждён"
      case "pending":
        return "Не распределён"
      case "cancelled":
        return "Отменён"
    }
  }

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString)
      return date.toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="grid gap-6">
          {/* Filters */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Проекты ({projects.length})</CardTitle>
                <div className="flex items-center gap-2">
                  {generateInfo && (
                    <p className="text-sm text-muted-foreground">{generateInfo}</p>
                  )}
                  <Button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending || !!tagTaskId}
                    variant="outline"
                    size="sm"
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    {generateMutation.isPending || tagTaskId ? "Генерация..." : "Сгенерировать теги"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            {tagProgress && tagProgress.total > 0 && (
              <div className="px-6 pb-2">
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-800 font-medium">
                    Генерация тегов: {tagProgress.current}/{tagProgress.total} ({Math.round((tagProgress.current / tagProgress.total) * 100)}%)
                  </p>
                  <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(tagProgress.current / tagProgress.total) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
            <CardContent>
              <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
                {/* Room Filter */}
                <div className="space-y-2">
                  <Label htmlFor="room-filter">Зал</Label>
                  <Select value={roomFilter} onValueChange={setRoomFilter}>
                    <SelectTrigger id="room-filter">
                      <SelectValue placeholder="Все залы" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Все залы</SelectItem>
                      {coverageData?.map((room) => (
                        <SelectItem key={room.room_id} value={room.room_id}>
                          {room.room_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Status Filter */}
                <div className="space-y-2">
                  <Label htmlFor="status-filter">Статус</Label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger id="status-filter">
                      <SelectValue placeholder="Все статусы" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Все статусы</SelectItem>
                      <SelectItem value="confirmed">Подтверждён</SelectItem>
                      <SelectItem value="pending">Не распределён</SelectItem>
                      <SelectItem value="cancelled">Отменён</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Search */}
                <div className="space-y-2">
                  <Label htmlFor="search">Поиск</Label>
                  <Input
                    id="search"
                    placeholder="Поиск по названию или автору..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Projects List */}
          <Card>
            <CardContent className="pt-6">
              {projects.length === 0 ? (
                !roomFilter && !statusFilter && !searchQuery ? (
                  <PageEmptyState
                    icon={FolderOpen}
                    title="Проекты ещё не загружены"
                    description="Загрузите проекты на странице Импорта."
                    actionLabel="Перейти к импорту"
                    actionLink="/import"
                  />
                ) : (
                  <p className="text-muted-foreground text-center py-8">Нет проектов</p>
                )
              ) : (
                <div className="space-y-3">
                  {projects.map((project) => (
                    <Link
                      key={project.id}
                      to={`/projects/${project.id}`}
                      className="block p-4 border rounded-lg hover:bg-muted/30 cursor-pointer"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium">{project.title}</p>
                          <p className="text-sm text-muted-foreground mt-1">{project.author}</p>
                          {project.track && (
                            <p className="text-sm text-muted-foreground mt-1">
                              <span className="font-medium">Трек:</span> {project.track}
                            </p>
                          )}
                          <p className="text-sm text-muted-foreground mt-1">{project.room_name}</p>
                          {project.start_time && project.start_time !== "TBD" && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {formatTime(project.start_time)} - {formatTime(project.end_time)}
                            </p>
                          )}
                          <div className="flex flex-wrap gap-2 mt-2">
                            {project.tags.map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-1 bg-muted text-xs rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-sm ${getStatusColor(
                            project.status
                          )}`}
                        >
                          {getStatusText(project.status)}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
    </div>
  )
}
