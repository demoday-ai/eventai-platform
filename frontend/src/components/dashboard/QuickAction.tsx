import { useNavigate } from "react-router-dom"
import { ArrowRight, Zap } from "lucide-react"
import { Button } from "../ui/button"
import { Card, CardContent } from "../ui/card"
import { usePipelineStatus } from "../../hooks/usePipelineStatus"

export function QuickAction() {
  const { data } = usePipelineStatus()
  const navigate = useNavigate()

  if (!data?.next_action) return null

  const { label, link } = data.next_action

  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardContent className="flex items-center gap-4 py-4">
        <Zap className="w-5 h-5 text-blue-600 shrink-0" />
        <p className="flex-1 text-sm font-medium">{label}</p>
        <Button
          size="sm"
          variant="default"
          onClick={() => navigate(link)}
          className="shrink-0"
        >
          Перейти
          <ArrowRight className="w-4 h-4 ml-1" />
        </Button>
      </CardContent>
    </Card>
  )
}
