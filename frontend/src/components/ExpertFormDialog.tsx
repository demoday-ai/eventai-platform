import { useState, useEffect } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import {
  createExpert,
  updateExpert,
  type ExpertListItem,
} from "../lib/api-client"

interface ExpertFormDialogProps {
  mode: "create" | "edit"
  expert?: ExpertListItem | null
  onClose: () => void
}

export function ExpertFormDialog({ mode, expert, onClose }: ExpertFormDialogProps) {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [telegram, setTelegram] = useState("")
  const [position, setPosition] = useState("")
  const [tagsInput, setTagsInput] = useState("")
  const [validationError, setValidationError] = useState("")

  useEffect(() => {
    if (mode === "edit" && expert) {
      setName(expert.name)
      setTelegram(expert.telegram_username || "")
      setPosition(expert.position || "")
      setTagsInput(expert.tags.join(", "))
    }
  }, [mode, expert])

  const createMutation = useMutation({
    mutationFn: () =>
      createExpert({
        name,
        telegram_username: telegram || null,
        position: position || null,
        tags: tagsInput ? tagsInput.split(",").map((t) => t.trim()).filter(Boolean) : [],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experts"] })
      onClose()
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      updateExpert(expert!.id, {
        name,
        telegram_username: telegram || null,
        position: position || null,
        tags: tagsInput ? tagsInput.split(",").map((t) => t.trim()).filter(Boolean) : [],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experts"] })
      onClose()
    },
  })

  const mutation = mode === "create" ? createMutation : updateMutation
  const isPending = mutation.isPending

  const handleSubmit = () => {
    setValidationError("")
    if (!name.trim()) {
      setValidationError("Имя обязательно")
      return
    }
    mutation.mutate()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="expert-dialog">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>
            {mode === "create" ? "Добавить эксперта" : "Редактировать эксперта"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="expert-name">Имя</Label>
            <Input
              id="expert-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Имя эксперта"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="expert-telegram">Telegram</Label>
            <Input
              id="expert-telegram"
              value={telegram}
              onChange={(e) => setTelegram(e.target.value)}
              placeholder="@username"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="expert-position">Должность</Label>
            <Input
              id="expert-position"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              placeholder="Должность"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="expert-tags">Теги (через запятую)</Label>
            <Input
              id="expert-tags"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="NLP, CV, ML"
            />
          </div>

          {validationError && (
            <p className="text-sm text-red-500">{validationError}</p>
          )}
          {mutation.isError && (
            <p className="text-sm text-red-500">
              Ошибка: {mutation.error instanceof Error ? mutation.error.message : "Неизвестная ошибка"}
            </p>
          )}

          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onClose} disabled={isPending}>
              Отмена
            </Button>
            <Button onClick={handleSubmit} disabled={isPending}>
              {isPending ? "Сохранение..." : "Сохранить"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
