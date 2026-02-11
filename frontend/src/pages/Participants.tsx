import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { UsersRound, Download, Send } from "lucide-react"
import { Card, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import {
  getGuests,
  exportGuests,
  isNoEventError,
  type GuestListItem,
} from "../lib/api-client"

const SUBTYPE_LABELS: Record<string, string> = {
  student: "Студент",
  applicant: "Абитуриент",
  other: "Другой",
}

const SUBTYPE_ICONS: Record<string, string> = {
  student: "\uD83C\uDF93",
  applicant: "\uD83D\uDCDA",
  business: "\uD83E\uDD1D",
  other: "\uD83D\uDC64",
}

function SubtypeBadge({ subtype }: { subtype: string | null }) {
  if (!subtype) return <span className="text-muted-foreground">—</span>
  const icon = SUBTYPE_ICONS[subtype] || ""
  const label = SUBTYPE_LABELS[subtype] || subtype
  return (
    <span className="px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-800">
      {icon} {label}
    </span>
  )
}

export function Participants() {
  const [search, setSearch] = useState("")
  const [subtypeFilter, setSubtypeFilter] = useState<string>("all")

  useEffect(() => {
    document.title = `${APP_NAME} - Участники`
  }, [])

  const subtypeParam = subtypeFilter !== "all" ? subtypeFilter : undefined
  const { data: guests, isLoading, isError, error } = useQuery({
    queryKey: ["participants", search, subtypeParam],
    queryFn: () =>
      getGuests({
        source: "import",
        ...(search ? { search } : {}),
        ...(subtypeParam ? { subtype: subtypeParam } : {}),
      }),
  })

  const exportMutation = useMutation({
    mutationFn: exportGuests,
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `participants_${new Date().toISOString().split("T")[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
    onError: (err) => {
      console.error("Export error:", err)
      alert(`Ошибка экспорта: ${err instanceof Error ? err.message : "Неизвестная ошибка"}`)
    },
  })

  const filteredGuests = useMemo(() => guests ?? undefined, [guests])

  const segmentParams = new URLSearchParams()
  segmentParams.set("segment_role", "guest")
  if (subtypeParam) segmentParams.set("segment_subtype", subtypeParam)

  return (
    <div className="grid gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold">
          Участники{" "}
          {filteredGuests && (
            <span className="text-muted-foreground text-lg font-normal">
              ({filteredGuests.length})
            </span>
          )}
        </h2>
        <div className="flex gap-2 flex-wrap">
          {filteredGuests && filteredGuests.length > 0 && (
            <Link to={`/messaging?${segmentParams.toString()}`}>
              <Button variant="outline" size="sm">
                <Send className="h-4 w-4 mr-1" />
                Рассылка
              </Button>
            </Link>
          )}
          {filteredGuests && filteredGuests.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                exportMutation.mutate({
                  search,
                  subtype: subtypeParam,
                  source: "import",
                })
              }
              disabled={exportMutation.isPending}
            >
              <Download className="h-4 w-4 mr-1" />
              {exportMutation.isPending ? "Экспорт..." : "Экспорт"}
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Поиск по имени или @telegram..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="sm:max-w-sm"
        />
        <Select value={subtypeFilter} onValueChange={setSubtypeFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Тип" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все типы</SelectItem>
            <SelectItem value="student">Студенты</SelectItem>
            <SelectItem value="applicant">Абитуриенты</SelectItem>
            <SelectItem value="other">Другие</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Загрузка...</p>}
      {isError && isNoEventError(error) && (
        <PageEmptyState
          icon={UsersRound}
          title="Создайте мероприятие"
          description="Создайте мероприятие, чтобы начать работу с участниками."
          actionLabel="Перейти к мероприятию"
          actionLink="/event"
        />
      )}
      {isError && !isNoEventError(error) && (
        <p className="text-sm text-red-500">Ошибка загрузки участников</p>
      )}

      {filteredGuests && filteredGuests.length === 0 && !search && subtypeFilter === "all" && (
        <PageEmptyState
          icon={UsersRound}
          title="Участники не загружены"
          description="Загрузите участников через импорт данных."
          actionLabel="Перейти к импорту"
          actionLink="/import"
        />
      )}
      {filteredGuests && filteredGuests.length === 0 && (search || subtypeFilter !== "all") && (
        <p className="text-sm text-muted-foreground">Участники не найдены</p>
      )}

      {filteredGuests && filteredGuests.length > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Имя</th>
                    <th className="pb-2 font-medium">Telegram</th>
                    <th className="pb-2 font-medium">Тип</th>
                    <th className="pb-2 font-medium text-center">В боте?</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGuests.map((guest: GuestListItem) => (
                    <tr
                      key={guest.id}
                      className="border-b last:border-0 hover:bg-muted/50"
                    >
                      <td className="py-2">{guest.full_name}</td>
                      <td className="py-2 text-muted-foreground">
                        {guest.username ? `@${guest.username}` : "—"}
                      </td>
                      <td className="py-2">
                        <SubtypeBadge subtype={guest.guest_subtype} />
                      </td>
                      <td className="py-2 text-center">
                        {!guest.telegram_user_id.startsWith("guest-") ? (
                          <span className="text-green-600 font-medium">{"\u2713"}</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
