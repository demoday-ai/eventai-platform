import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { FolderOpen, Sparkles } from "lucide-react"
import { getProjects, getCoverage, generateProjectTags, isNoEventError, type ProjectListItem } from "../lib/api-client"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { Label } from "../components/ui/label"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import { useBackgroundJobs } from "../contexts/BackgroundJobsContext"

export function ProjectsList() {
  const queryClient = useQueryClient()
  const { jobs, startTagGeneration } = useBackgroundJobs()
  const [roomFilter, setRoomFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [generateInfo, setGenerateInfo] = useState<string | null>(null)

  // Check if tag generation is running
  const isGenerating = jobs.some(
    (job) =>
      job.type === "tag-generation" &&
      (job.status === "running" || job.status === "pending")
  )

  // Set page title
  useEffect(() => {
    document.title = `${APP_NAME} - Проекты`
  }, [])

  // Invalidate queries when tag generation completes
  useEffect(() => {
    const completedJobs = jobs.filter(
      (job) => job.type === "tag-generation" && job.status === "completed"
    )

    if (completedJobs.length > 0) {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
    }
  }, [jobs, queryClient])

  const generateMutation = useMutation({
    mutationFn: generateProjectTags,
    onSuccess: (result) => {
      if (result.task_id) {
        // Start tracking in global context
        startTagGeneration(result.task_id)
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

  // Count projects without tags
  const projectsWithoutTags = projects.filter((p) => p.tags.length === 0).length
  const allTagged = projects.length > 0 && projectsWithoutTags === 0

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
                    disabled={generateMutation.isPending || isGenerating || allTagged}
                    variant="outline"
                    size="sm"
                    title={allTagged ? "У всех проектов уже есть теги" : `Проектов без тегов: ${projectsWithoutTags}`}
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    {generateMutation.isPending || isGenerating
                      ? "Генерация..."
                      : allTagged
                        ? "Все теги назначены"
                        : `Сгенерировать теги (${projectsWithoutTags})`}
                  </Button>
                </div>
              </div>
            </CardHeader>
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
