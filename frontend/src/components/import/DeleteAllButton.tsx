import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { Button } from "../ui/button"

interface DeleteAllButtonProps {
  label: string
  count?: number
  deleteFn: () => Promise<{ deleted: number }>
  onDeleted?: (count: number) => void
}

export function DeleteAllButton({ label, count, deleteFn, onDeleted }: DeleteAllButtonProps) {
  const queryClient = useQueryClient()
  const [showConfirm, setShowConfirm] = useState(false)

  const mutation = useMutation({
    mutationFn: deleteFn,
    onSuccess: (data) => {
      setShowConfirm(false)
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
      onDeleted?.(data.deleted)
    },
  })

  if (!showConfirm) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="text-destructive border-destructive/30 hover:bg-destructive/10"
        onClick={() => setShowConfirm(true)}
      >
        <Trash2 className="h-4 w-4 mr-1" />
        {label}
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2 p-3 border border-destructive/30 rounded-md bg-destructive/5">
      <p className="text-sm">
        Удалить {label.toLowerCase()}
        {count !== undefined && count > 0 ? ` (${count})` : ""}?
        <span className="text-destructive font-medium ml-1">Это действие необратимо.</span>
      </p>
      <Button
        variant="destructive"
        size="sm"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Удаление..." : "Удалить"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowConfirm(false)}
        disabled={mutation.isPending}
      >
        Отмена
      </Button>
    </div>
  )
}
