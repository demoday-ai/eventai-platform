import { Link } from "react-router-dom"
import type { LucideIcon } from "lucide-react"
import { Button } from "./button"
import { Card, CardContent } from "./card"

interface PageEmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  actionLabel?: string
  actionLink?: string
}

export function PageEmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionLink,
}: PageEmptyStateProps) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <Icon className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-muted-foreground mb-6 max-w-md">{description}</p>
        {actionLabel && actionLink && (
          <Button asChild>
            <Link to={actionLink}>{actionLabel}</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
