import { useNavigate } from "react-router-dom"
import { Button } from "../ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import type { RoomCoverage } from "../../lib/api-client"

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  gap: { label: "Пробел", className: "bg-red-100 text-red-800" },
  partial: { label: "Частично", className: "bg-yellow-100 text-yellow-800" },
  covered: { label: "Покрыт", className: "bg-green-100 text-green-800" },
  excellent: { label: "Отлично", className: "bg-green-100 text-green-800" },
  excess: { label: "Перебор", className: "bg-blue-100 text-blue-800" },
}

interface DashboardCoverageTableProps {
  data: RoomCoverage[]
}

export function DashboardCoverageTable({ data }: DashboardCoverageTableProps) {
  const navigate = useNavigate()

  if (data.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Покрытие залов</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 font-medium">Зал</th>
                <th className="pb-2 font-medium text-center">Проекты</th>
                <th className="pb-2 font-medium text-center">Эксперты</th>
                <th className="pb-2 font-medium text-center">Статус</th>
                <th className="pb-2 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((room) => {
                const status = STATUS_CONFIG[room.coverage_status] || STATUS_CONFIG.gap
                return (
                  <tr key={room.room_id} className="border-b last:border-0">
                    <td className="py-2 font-medium">{room.room_name}</td>
                    <td className="py-2 text-center">{room.projects_count}</td>
                    <td className="py-2 text-center">{room.confirmed_experts}</td>
                    <td className="py-2 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${status.className}`}>
                        {status.label}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/coverage?room=${room.room_id}`)}
                      >
                        Детали
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
