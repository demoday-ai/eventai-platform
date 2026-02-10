import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { APP_NAME } from "../lib/constants"
import {
  getOrganizers, addOrganizer, removeOrganizer,
  getLlmModels, getCurrentLlmModel, updateLlmModel,
  getLlmApiKeys, addLlmApiKey, deleteLlmApiKey, checkLlmKeys,
  type OrganizerItem,
  type LlmApiKeyItem,
} from "../lib/api-client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select"

export function Settings() {
  useEffect(() => {
    document.title = `${APP_NAME} - Настройки`
  }, [])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Настройки</h2>
      <LlmConfigSection />
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

function LlmConfigSection() {
  const queryClient = useQueryClient()
  const [showAddKeyForm, setShowAddKeyForm] = useState(false)
  const [newApiKey, setNewApiKey] = useState("")

  const { data: modelsData } = useQuery({
    queryKey: ["llm-models"],
    queryFn: getLlmModels,
  })

  const { data: currentModelData } = useQuery({
    queryKey: ["llm-current-model"],
    queryFn: getCurrentLlmModel,
  })

  const { data: keysData, isLoading: keysLoading } = useQuery({
    queryKey: ["llm-keys"],
    queryFn: getLlmApiKeys,
    refetchInterval: 30000, // Refresh every 30s for live stats
  })

  const updateModelMutation = useMutation({
    mutationFn: updateLlmModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-current-model"] })
    },
  })

  const addKeyMutation = useMutation({
    mutationFn: addLlmApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-keys"] })
      setShowAddKeyForm(false)
      setNewApiKey("")
    },
  })

  const deleteKeyMutation = useMutation({
    mutationFn: deleteLlmApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-keys"] })
    },
  })

  const checkKeysMutation = useMutation({
    mutationFn: checkLlmKeys,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-keys"] })
    },
  })

  const getStatusBadge = (key: LlmApiKeyItem) => {
    if (!key.available && key.cooldown_remaining > 0) {
      return <span className="text-amber-600">Cooldown ({Math.ceil(key.cooldown_remaining)}s)</span>
    }
    if (key.fail_count > 3) {
      return <span className="text-red-600">Failed</span>
    }
    if (key.fail_count > 0) {
      return <span className="text-amber-600">Warning ({key.fail_count} fails)</span>
    }
    return <span className="text-green-600">OK</span>
  }

  const currentModel = modelsData?.models.find(m => m.id === currentModelData?.model_id)

  return (
    <Card>
      <CardHeader>
        <CardTitle>LLM Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label>Модель</Label>
          <div className="flex items-center gap-4">
            <Select
              value={currentModelData?.model_id}
              onValueChange={(value) => updateModelMutation.mutate(value)}
              disabled={updateModelMutation.isPending}
            >
              <SelectTrigger className="w-80">
                <SelectValue placeholder="Выберите модель" />
              </SelectTrigger>
              <SelectContent>
                {modelsData?.models.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    {model.name} (${model.input_price}/${model.output_price} per 1M)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {currentModel && (
              <div className="text-sm text-muted-foreground">
                Input: ${currentModel.input_price}/1M | Output: ${currentModel.output_price}/1M |
                Context: {currentModel.context.toLocaleString()}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>API ключи</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={() => checkKeysMutation.mutate()}
              disabled={checkKeysMutation.isPending}
            >
              {checkKeysMutation.isPending ? "Проверка..." : "Проверить все"}
            </Button>
          </div>

          {keysLoading && <p className="text-muted-foreground">Загрузка...</p>}

          {keysData && keysData.keys.length > 0 && (
            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left py-2 px-4">Ключ</th>
                    <th className="text-left py-2 px-4">Статус</th>
                    <th className="text-left py-2 px-4">Последнее использование</th>
                    <th className="text-left py-2 px-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {keysData.keys.map((key) => (
                    <tr key={key.id} className="border-t">
                      <td className="py-2 px-4 font-mono">...{key.key_suffix}</td>
                      <td className="py-2 px-4">{getStatusBadge(key)}</td>
                      <td className="py-2 px-4 text-muted-foreground">
                        {key.last_success_at
                          ? new Date(key.last_success_at).toLocaleString("ru-RU")
                          : "—"}
                      </td>
                      <td className="py-2 px-4">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteKeyMutation.mutate(key.id)}
                          disabled={deleteKeyMutation.isPending}
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

          {keysData && keysData.keys.length === 0 && (
            <p className="text-muted-foreground">Нет ключей в базе данных</p>
          )}

          {!showAddKeyForm && (
            <Button variant="outline" onClick={() => setShowAddKeyForm(true)}>
              Добавить ключ
            </Button>
          )}

          {showAddKeyForm && (
            <div className="border rounded-md p-4 space-y-3">
              <div className="space-y-2">
                <Label htmlFor="api-key">API Key</Label>
                <Input
                  id="api-key"
                  value={newApiKey}
                  onChange={(e) => setNewApiKey(e.target.value)}
                  placeholder="sk-or-v1-..."
                  type="password"
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => addKeyMutation.mutate(newApiKey)}
                  disabled={addKeyMutation.isPending || !newApiKey.trim()}
                >
                  {addKeyMutation.isPending ? "Добавление..." : "Добавить"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowAddKeyForm(false)
                    setNewApiKey("")
                  }}
                >
                  Отмена
                </Button>
              </div>
              {addKeyMutation.isError && (
                <p className="text-sm text-red-500">
                  Ошибка: {addKeyMutation.error instanceof Error ? addKeyMutation.error.message : "Не удалось добавить"}
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
