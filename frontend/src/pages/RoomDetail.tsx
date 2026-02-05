import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams, useNavigate } from "react-router-dom"
import { getRoomDetail, updateRoom, type ExpertInfo, type ProjectInfo } from "../lib/api-client"
import { Button } from "../components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"

export function RoomDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ["roomDetail", id],
    queryFn: () => getRoomDetail(id!),
    enabled: !!id,
  })

  const [roomName, setRoomName] = useState("")
  const [roomTheme, setRoomTheme] = useState("")
  const [roomMessage, setRoomMessage] = useState<string | null>(null)

  useEffect(() => {
    if (data?.room) {
      setRoomName(data.room.name || "")
      setRoomTheme(data.room.theme_rationale ?? data.room.description ?? "")
    }
  }, [data?.room])

  const updateMutation = useMutation({
    mutationFn: (body: { name?: string | null; theme_rationale?: string | null }) =>
      updateRoom(id!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roomDetail", id] })
      setRoomMessage("Сохранено")
    },
    onError: (err) => {
      setRoomMessage(err instanceof Error ? err.message : "Не удалось сохранить")
    },
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    if (!data?.room) return
    const body: { name?: string | null; theme_rationale?: string | null } = {}
    const trimmedName = roomName.trim()
    const trimmedTheme = roomTheme.trim()
    const currentTheme = data.room.theme_rationale ?? data.room.description ?? ""

    if (trimmedName && trimmedName !== data.room.name) {
      body.name = trimmedName
    }
    if (trimmedTheme && trimmedTheme !== currentTheme) {
      body.theme_rationale = trimmedTheme
    }

    if (!body.name && !body.theme_rationale) {
      setRoomMessage("Нет изменений")
      return
    }
    setRoomMessage(null)
    updateMutation.mutate(body)
  }

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
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Загрузка...</p>
      </div>
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

  if (!data) {
    return null
  }

  return (
    <div className="grid gap-6">
      <div>
        <Button variant="ghost" onClick={() => navigate(-1)}>
          ← Назад
        </Button>
      </div>
      {/* Room info */}
      <Card>
        <CardHeader>
          <CardTitle>{data.room.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="room-name">Название зала</Label>
              <Input
                id="room-name"
                value={roomName}
                onChange={(e) => {
                  setRoomName(e.target.value)
                  setRoomMessage(null)
                }}
                disabled={updateMutation.isPending}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="room-theme">Тематика зала</Label>
              <textarea
                id="room-theme"
                className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                value={roomTheme}
                onChange={(e) => {
                  setRoomTheme(e.target.value)
                  setRoomMessage(null)
                }}
                disabled={updateMutation.isPending}
              />
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
              </Button>
              {roomMessage && (
                <span
                  className={`text-sm ${
                    roomMessage === "Сохранено"
                      ? "text-green-600"
                      : roomMessage === "Нет изменений"
                        ? "text-muted-foreground"
                        : "text-red-500"
                  }`}
                >
                  {roomMessage}
                </span>
              )}
            </div>
          </form>
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
