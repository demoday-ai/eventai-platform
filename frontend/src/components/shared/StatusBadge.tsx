import React from "react"

export interface StatusBadgeProps {
  status: string | null
  variant?: "notification" | "expert" | "coverage" | "role"
}

const NOTIFICATION_STYLES: Record<string, { label: string; className: string }> = {
  sent: { label: "Отправлено", className: "bg-green-100 text-green-800" },
  failed: { label: "Ошибка", className: "bg-red-100 text-red-800" },
  pending: { label: "Ожидает", className: "bg-yellow-100 text-yellow-800" },
}

const EXPERT_STYLES: Record<string, { label: string; className: string }> = {
  confirmed: { label: "Подтверждён", className: "bg-green-100 text-green-800" },
  declined: { label: "Отклонён", className: "bg-red-100 text-red-800" },
  invited: { label: "Приглашён", className: "bg-yellow-100 text-yellow-800" },
  invite_ready: { label: "Готов к приглашению", className: "bg-yellow-100 text-yellow-800" },
  proposed: { label: "Предложен", className: "bg-gray-100 text-gray-700" },
  approved: { label: "Одобрен", className: "bg-gray-100 text-gray-700" },
}

const COVERAGE_STYLES: Record<string, { label: string; className: string }> = {
  full: { label: "Полное", className: "bg-green-100 text-green-800" },
  partial: { label: "Частичное", className: "bg-yellow-100 text-yellow-800" },
  none: { label: "Нет", className: "bg-red-100 text-red-800" },
}

const ROLE_STYLES: Record<string, { label: string; className: string }> = {
  guest: { label: "Гость", className: "bg-blue-100 text-blue-800" },
  business: { label: "Партнёр", className: "bg-amber-100 text-amber-800" },
}

const VARIANT_MAP: Record<string, Record<string, { label: string; className: string }>> = {
  notification: NOTIFICATION_STYLES,
  expert: EXPERT_STYLES,
  coverage: COVERAGE_STYLES,
  role: ROLE_STYLES,
}

const DEFAULT_STYLE = { label: "", className: "bg-gray-100 text-gray-700" }

export const StatusBadge = React.memo(function StatusBadge({
  status,
  variant = "notification",
}: StatusBadgeProps) {
  if (!status) return <span className="text-xs text-muted-foreground">—</span>

  const styles = VARIANT_MAP[variant] || NOTIFICATION_STYLES
  const { label, className } = styles[status] || { ...DEFAULT_STYLE, label: status }

  return (
    <span
      data-testid="status-badge"
      className={`px-2 py-0.5 rounded text-xs ${className}`}
    >
      {label}
    </span>
  )
})
