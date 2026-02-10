import { useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { APP_NAME } from "../lib/constants"
import { getRoomCoverageDetail } from "../lib/api-client"

function statusBadge(status: string) {
  switch (status) {
    case "confirmed":
      return <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">Подтв.</span>
    case "pending":
      return <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">Ожидает</span>
    case "declined":
      return <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">Отклонён</span>
    default:
      return <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-800">{status}</span>
  }
}

export function CoverageRoomDetail() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()

  useEffect(() => {
    document.title = `${APP_NAME} - Детали покрытия`
  }, [])

  const { data, isLoading, isError } = useQuery({
    queryKey: ["roomCoverageDetail", roomId],
    queryFn: () => getRoomCoverageDetail(roomId!),
    enabled: !!roomId,
  })

  if (isLoading) return <p className="text-muted-foreground p-4">Загрузка...</p>
  if (isError) return <p className="text-sm text-red-500 p-4">Ошибка загрузки данных</p>
  if (!data) return null

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => navigate("/experts")}>
          ← Назад
        </Button>
        <h2 className="text-2xl font-bold">{data.room_name}</h2>
      </div>

      {/* Room info */}
      <Card>
        <CardHeader>
          <CardTitle>Информация о зале</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">Проектов: <span className="font-medium">{data.project_count}</span></p>
          <div className="flex flex-wrap gap-1">
            {data.project_tags.map((tag) => (
              <span key={tag} className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                {tag}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Experts */}
      <Card>
        <CardHeader>
          <CardTitle>Эксперты ({data.experts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {data.experts.length === 0 ? (
            <p className="text-muted-foreground text-sm">Экспертов нет</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-4">Имя</th>
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Совпадение</th>
                    <th className="py-2 pr-4">Теги</th>
                    <th className="py-2">Бот</th>
                  </tr>
                </thead>
                <tbody>
                  {data.experts.map((expert) => (
                    <tr key={expert.expert_id} className="border-b">
                      <td className="py-2 pr-4 font-medium">{expert.name}</td>
                      <td className="py-2 pr-4">{statusBadge(expert.status)}</td>
                      <td className="py-2 pr-4">{(expert.match_score * 100).toFixed(0)}%</td>
                      <td className="py-2 pr-4">
                        <span className="text-xs text-muted-foreground">
                          {expert.tags.join(", ")}
                        </span>
                      </td>
                      <td className="py-2">
                        {expert.bot_started ? (
                          <span className="text-xs text-green-600">Запущен</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Uncovered tags */}
      {data.uncovered_tags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Непокрытые теги</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {data.uncovered_tags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">
                  {tag}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Candidates */}
      {data.candidates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Кандидаты ({data.candidates.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.candidates.map((c) => (
                <div key={c.expert_id} className="text-sm flex items-center gap-2">
                  <span className="font-medium">{c.name}</span>
                  <span className="text-xs text-muted-foreground">
                    теги: {c.matching_tags.join(", ")}
                  </span>
                  {c.current_rooms.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      (залы: {c.current_rooms.join(", ")})
                    </span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
