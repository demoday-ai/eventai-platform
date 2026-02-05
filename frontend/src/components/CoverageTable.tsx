import { useNavigate } from "react-router-dom"
import { CheckCircle, AlertCircle, XCircle } from "lucide-react"
import type { RoomCoverage } from "../lib/api-client"
import { Button } from "./ui/button"

interface CoverageTableProps {
  data: RoomCoverage[]
}

export function CoverageTable({ data }: CoverageTableProps) {
  const navigate = useNavigate()

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Нет данных о покрытии залов
      </div>
    )
  }

  const getStatusColor = (status: RoomCoverage["coverage_status"]) => {
    switch (status) {
      case "full":
        return "text-green-600 bg-green-50"
      case "partial":
        return "text-yellow-600 bg-yellow-50"
      case "none":
        return "text-red-600 bg-red-50"
    }
  }

  const getStatusIcon = (status: RoomCoverage["coverage_status"]) => {
    switch (status) {
      case "full":
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case "partial":
        return <AlertCircle className="w-4 h-4 text-yellow-600" />
      case "none":
        return <XCircle className="w-4 h-4 text-red-600" />
    }
  }

  const getStatusText = (status: RoomCoverage["coverage_status"]) => {
    switch (status) {
      case "full":
        return "Покрыт"
      case "partial":
        return "Частично"
      case "none":
        return "Не покрыт"
    }
  }

  return (
    <div className="rounded-md border">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="p-4 text-left text-sm font-medium">Зал</th>
            <th className="p-4 text-left text-sm font-medium">Проектов</th>
            <th className="p-4 text-left text-sm font-medium">Эксперты</th>
            <th className="p-4 text-left text-sm font-medium">Статус</th>
            <th className="p-4 text-left text-sm font-medium">Детали</th>
          </tr>
        </thead>
        <tbody>
          {data.map((room) => (
            <tr key={room.room_id} className="border-b last:border-0 hover:bg-muted/30">
              <td className="p-4 font-medium">{room.room_name}</td>
              <td className="p-4 text-muted-foreground">{room.projects_count}</td>
              <td className="p-4 text-muted-foreground">
                {room.confirmed_experts} / {room.total_experts}
              </td>
              <td className="p-4">
                <span
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${getStatusColor(
                    room.coverage_status
                  )}`}
                  data-status={room.coverage_status}
                >
                  <span>{getStatusIcon(room.coverage_status)}</span>
                  <span>{getStatusText(room.coverage_status)}</span>
                </span>
              </td>
              <td className="p-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/rooms/${room.room_id}`)}
                >
                  Детали
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
