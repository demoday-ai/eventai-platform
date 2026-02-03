import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useParams, useNavigate } from "react-router-dom"
import { getRoomDetail, type ExpertInfo, type ProjectInfo } from "../lib/api-client"
import { Button } from "../components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { APP_NAME } from "../lib/constants"

export function RoomDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ["roomDetail", id],
    queryFn: () => getRoomDetail(id!),
    enabled: !!id,
  })

  // Set page title
  useEffect(() => {
    if (data?.room.name) {
      document.title = `${APP_NAME} - ${data.room.name}`
    } else {
      document.title = `${APP_NAME} - Зал`
    }
  }, [data?.room.name])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-muted/30 flex items-center justify-center">
        <p className="text-muted-foreground">Загрузка...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-muted/30 flex items-center justify-center">
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

  if (!data) {
    return null
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            ← Назад
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6">
          {/* Room info */}
          <Card>
            <CardHeader>
              <CardTitle>{data.room.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{data.room.description}</p>
            </CardContent>
          </Card>

          {/* Experts */}
          <Card>
            <CardHeader>
              <CardTitle>Эксперты ({data.experts.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <ExpertsList experts={data.experts} />
            </CardContent>
          </Card>

          {/* Projects */}
          <Card>
            <CardHeader>
              <CardTitle>Проекты ({data.projects.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <ProjectsList projects={data.projects} />
            </CardContent>
          </Card>

          {/* Uncovered topics */}
          {data.uncovered_topics.length > 0 && (
            <Card className="border-yellow-200">
              <CardHeader>
                <CardTitle>Непокрытые тематики</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {data.uncovered_topics.map((topic) => (
                    <span
                      key={topic}
                      className="px-3 py-1 bg-yellow-50 text-yellow-900 rounded-full text-sm"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}

function ExpertsList({ experts }: { experts: ExpertInfo[] }) {
  if (experts.length === 0) {
    return <p className="text-muted-foreground">Нет экспертов</p>
  }

  const getStatusColor = (status: ExpertInfo["status"]) => {
    switch (status) {
      case "confirmed":
        return "text-green-600 bg-green-50"
      case "pending":
        return "text-yellow-600 bg-yellow-50"
      case "declined":
        return "text-red-600 bg-red-50"
    }
  }

  const getStatusText = (status: ExpertInfo["status"]) => {
    switch (status) {
      case "confirmed":
        return "Подтверждён"
      case "pending":
        return "Ожидает"
      case "declined":
        return "Отказался"
    }
  }

  return (
    <div className="space-y-3">
      {experts.map((expert) => (
        <div
          key={expert.id}
          className="p-4 border rounded-lg hover:bg-muted/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="font-medium">{expert.name}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {expert.tags.map((tag) => (
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
                expert.status
              )}`}
            >
              {getStatusText(expert.status)}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

function ProjectsList({ projects }: { projects: ProjectInfo[] }) {
  if (projects.length === 0) {
    return <p className="text-muted-foreground">Нет проектов</p>
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const getStatusColor = (status: ProjectInfo["status"]) => {
    switch (status) {
      case "confirmed":
        return "text-green-600 bg-green-50"
      case "pending":
        return "text-yellow-600 bg-yellow-50"
      case "cancelled":
        return "text-red-600 bg-red-50"
    }
  }

  const getStatusText = (status: ProjectInfo["status"]) => {
    switch (status) {
      case "confirmed":
        return "Подтверждён"
      case "pending":
        return "Ожидает"
      case "cancelled":
        return "Отменён"
    }
  }

  return (
    <div className="space-y-3">
      {projects.map((project) => (
        <div
          key={project.id}
          className="p-4 border rounded-lg hover:bg-muted/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="font-medium">{project.title}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {project.author}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {formatTime(project.start_time)} - {formatTime(project.end_time)}
              </p>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-sm ${getStatusColor(
                project.status
              )}`}
            >
              {getStatusText(project.status)}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
