import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { ExpertFormDialog } from "../components/ExpertFormDialog"
import { APP_NAME } from "../lib/constants"
import { getExperts, type ExpertListItem } from "../lib/api-client"

export function ExpertList() {
  const [search, setSearch] = useState("")
  const [dialog, setDialog] = useState<{
    mode: "create" | "edit"
    expert?: ExpertListItem
  } | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Список экспертов`
  }, [])

  const { data: experts, isLoading, isError } = useQuery({
    queryKey: ["experts", search],
    queryFn: () => getExperts(search ? { search } : undefined),
  })

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Список экспертов</h2>
        <div className="flex gap-2">
          <Link to="/experts">
            <Button variant="outline">Матчинг</Button>
          </Link>
          <Button onClick={() => setDialog({ mode: "create" })}>
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
