import { useNavigate } from "react-router-dom"
import { FolderOpen } from "lucide-react"
import { Button } from "../ui/button"
import { Card, CardContent } from "../ui/card"

export function EmptyState() {
  const navigate = useNavigate()

  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <FolderOpen className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">Нет активного мероприятия</h3>
        <p className="text-muted-foreground mb-6 max-w-md">
          Создайте мероприятие и загрузите данные, чтобы начать подготовку Demo Day.
        </p>
        <Button onClick={() => navigate("/import")}>
          Перейти к импорту
        </Button>
      </CardContent>
    </Card>
  )
}
