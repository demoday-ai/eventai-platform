import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { getProjects, getCoverage, isNoEventError, type ProjectListItem } from "../lib/api-client"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"

export function ProjectsList() {
  const [roomFilter, setRoomFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState<string>("")

  // Set page title
  useEffect(() => {
    document.title = `${APP_NAME} - Проекты`
  }, [])

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
      <div className="flex items-center justify-center py-16">
        <Card className="border-dashed">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              Нет активного мероприятия. Загрузите проекты на вкладке «Импорт данных», чтобы создать мероприятие.
            </p>
          </CardContent>
        </Card>
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
        return "Ожидает"
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
              <CardTitle>Проекты ({projects.length})</CardTitle>
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
                      <SelectItem value="pending">Ожидает</SelectItem>
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
                <p className="text-muted-foreground text-center py-8">Нет проектов</p>
              ) : (
                <div className="space-y-3">
                  {projects.map((project) => (
                    <div
                      key={project.id}
                      className="p-4 border rounded-lg hover:bg-muted/30 cursor-pointer"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium">{project.title}</p>
                          <p className="text-sm text-muted-foreground mt-1">{project.author}</p>
                          <p className="text-sm text-muted-foreground mt-1">{project.room_name}</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            {formatTime(project.start_time)} - {formatTime(project.end_time)}
                          </p>
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
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
    </div>
  )
}
