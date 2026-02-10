import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import {
  getOrganizers, addOrganizer, removeOrganizer,
  type OrganizerItem,
} from "../lib/api-client"

export function Settings() {
  useEffect(() => {
    document.title = `${APP_NAME} - Настройки`
  }, [])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Настройки</h2>
      <OrganizersSection />
    </div>
  )
}

function OrganizersSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [username, setUsername] = useState("")
  const [orgName, setOrgName] = useState("")

  const { data: organizers, isLoading } = useQuery<OrganizerItem[]>({
    queryKey: ["organizers"],
    queryFn: getOrganizers,
  })

  const addMutation = useMutation({
    mutationFn: addOrganizer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizers"] })
      setShowForm(false)
      setUsername("")
      setOrgName("")
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeOrganizer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizers"] })
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) return
    addMutation.mutate({
      telegram_id: "",
      telegram_username: username.trim(),
      name: orgName.trim() || null,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Организаторы</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <p className="text-muted-foreground">Загрузка...</p>}

        {organizers && organizers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4">Username</th>
                  <th className="text-left py-2 pr-4">Имя</th>
                  <th className="text-left py-2 pr-4">Добавлен</th>
                  <th className="text-left py-2"></th>
                </tr>
              </thead>
              <tbody>
                {organizers.map((org: OrganizerItem) => (
                  <tr key={org.id} className="border-b">
                    <td className="py-2 pr-4">{org.telegram_username || "—"}</td>
                    <td className="py-2 pr-4">{org.name || "—"}</td>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {new Date(org.created_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td className="py-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => removeMutation.mutate(org.id)}
                        disabled={removeMutation.isPending}
                      >
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {organizers && organizers.length === 0 && (
          <p className="text-muted-foreground">Нет организаторов</p>
        )}

        {!showForm && (
          <Button variant="outline" onClick={() => setShowForm(true)}>
            Добавить организатора
          </Button>
        )}

        {showForm && (
          <form onSubmit={handleAdd} className="space-y-3 border rounded-md p-4">
            <div className="space-y-2">
              <Label htmlFor="org-username">Username *</Label>
              <Input
                id="org-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="@username"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-name">Имя</Label>
              <Input
                id="org-name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Иван Иванов"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button type="submit" disabled={addMutation.isPending || !username.trim()}>
                {addMutation.isPending ? "Добавление..." : "Добавить"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>
                Отмена
              </Button>
            </div>
            {addMutation.isError && (
              <p className="text-sm text-red-500">
                Ошибка: {addMutation.error instanceof Error ? addMutation.error.message : "Не удалось добавить"}
              </p>
            )}
          </form>
        )}
      </CardContent>
    </Card>
  )
}
