import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { ExpertFormDialog } from "../components/ExpertFormDialog"
import { StatusBadge } from "../components/shared/StatusBadge"
import { APP_NAME } from "../lib/constants"
import { getExperts, updateExpertStatus, type ExpertListItem } from "../lib/api-client"

function canChangeStatus(status: string | null): boolean {
  return status !== null && status !== "confirmed" && status !== "declined"
}

export function ExpertList() {
  const [search, setSearch] = useState("")
  const [dialog, setDialog] = useState<{
    mode: "create" | "edit"
    expert?: ExpertListItem
  } | null>(null)
  const queryClient = useQueryClient()

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateExpertStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experts"] })
    },
  })

  useEffect(() => {
    document.title = `${APP_NAME} - Список экспертов`
  }, [])

  const { data: experts, isLoading, isError } = useQuery({
    queryKey: ["experts", search],
    queryFn: () => getExperts(search ? { search } : undefined),
  })

  return (
    <div className="grid gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold">Список экспертов</h2>
        <div className="flex gap-2">
          <Link to="/experts">
            <Button variant="outline" className="flex-1 sm:flex-none">Матчинг</Button>
          </Link>
          <Button onClick={() => setDialog({ mode: "create" })} className="flex-1 sm:flex-none">
            Добавить эксперта
          </Button>
        </div>
      </div>

      <Input
        placeholder="Поиск по имени или Telegram..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {isLoading && <p className="text-sm text-muted-foreground">Загрузка...</p>}
      {isError && <p className="text-sm text-red-500">Ошибка загрузки списка экспертов</p>}

      {experts && experts.length === 0 && (
        <p className="text-sm text-muted-foreground">Эксперты не найдены</p>
      )}

      {experts && experts.length > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Имя</th>
                    <th className="pb-2 font-medium">Telegram</th>
                    <th className="pb-2 font-medium">Должность</th>
                    <th className="pb-2 font-medium">Теги</th>
                    <th className="pb-2 font-medium">Статус</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {experts.map((expert) => (
                    <tr key={expert.id} className="border-b last:border-0">
                      <td className="py-2">{expert.name}</td>
                      <td className="py-2 text-muted-foreground">
                        {expert.telegram_username ? `@${expert.telegram_username}` : "—"}
                      </td>
                      <td className="py-2 text-muted-foreground">
                        {expert.position || "—"}
                      </td>
                      <td className="py-2">
                        <div className="flex flex-wrap gap-1">
                          {expert.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-1.5 py-0.5 bg-muted text-xs rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-2">
                        <div className="flex items-center gap-1">
                          <StatusBadge status={expert.assignment_status} variant="expert" />
                          {canChangeStatus(expert.assignment_status) && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-green-700 h-6 px-1.5 text-xs"
                                disabled={statusMutation.isPending}
                                onClick={() => statusMutation.mutate({ id: expert.id, status: "confirmed" })}
                              >
                                Подтвердить
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-700 h-6 px-1.5 text-xs"
                                disabled={statusMutation.isPending}
                                onClick={() => statusMutation.mutate({ id: expert.id, status: "declined" })}
                              >
                                Отклонить
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="py-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDialog({ mode: "edit", expert })}
                        >
                          Редактировать
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {dialog && (
        <ExpertFormDialog
          mode={dialog.mode}
          expert={dialog.expert || null}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  )
}
