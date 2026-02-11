import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
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
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: deleteFn,
    onSuccess: (data) => {
      setShowConfirm(false)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
      onDeleted?.(data.deleted)
    },
    onError: (err: Error) => {
      const axErr = err as AxiosError<{ detail: string }>
      setError(axErr.response?.data?.detail || err.message)
    },
  })

  if (!showConfirm) {
    return (
      <div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive border-destructive/30 hover:bg-destructive/10"
          onClick={() => { setShowConfirm(true); setError(null) }}
        >
          <Trash2 className="h-4 w-4 mr-1" />
          {label}
        </Button>
        {error && <p className="text-sm text-red-500 mt-1">Ошибка: {error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 p-3 border border-destructive/30 rounded-md bg-destructive/5">
        <p className="text-sm">
          Удалить {label.toLowerCase()}
          {count !== undefined && count > 0 ? ` (${count})` : ""}?
          <span className="text-destructive font-medium ml-1">Это действие необратимо.</span>
        </p>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => { setError(null); mutation.mutate() }}
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
      {error && <p className="text-sm text-red-500">Ошибка: {error}</p>}
    </div>
  )
}
