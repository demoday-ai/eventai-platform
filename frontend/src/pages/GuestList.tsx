import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"
import { APP_NAME } from "../lib/constants"
import {
  getGuests,
  getGuestDetail,
  type GuestListItem,
  type GuestDetailResponse,
} from "../lib/api-client"

const SUBTYPE_LABELS: Record<string, string> = {
  student: "Студент",
  applicant: "Абитуриент",
  other: "Другой",
}

const SUBTYPE_STYLES: Record<string, string> = {
  student: "bg-blue-100 text-blue-800",
  applicant: "bg-purple-100 text-purple-800",
  other: "bg-gray-100 text-gray-700",
}

const CONTACT_STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает",
  approved: "Одобрен",
  rejected: "Отклонён",
  expired: "Истёк",
}

function SubtypeBadge({ subtype }: { subtype: string | null }) {
  if (!subtype) return <span className="text-xs text-muted-foreground">—</span>
  return (
    <span
      className={`px-1.5 py-0.5 text-xs rounded ${SUBTYPE_STYLES[subtype] || "bg-gray-100 text-gray-700"}`}
    >
      {SUBTYPE_LABELS[subtype] || subtype}
    </span>
  )
}

function GuestDetailPanel({ guestId }: { guestId: string }) {
  const { data, isLoading, isError } = useQuery<GuestDetailResponse>({
    queryKey: ["guest-detail", guestId],
    queryFn: () => getGuestDetail(guestId),
  })

  if (isLoading) return <div className="p-4 text-sm text-muted-foreground">Загрузка...</div>
  if (isError) return <div className="p-4 text-sm text-red-500">Ошибка загрузки</div>
  if (!data) return null

  const { profile, business_profile, recommendations, contact_requests } = data

  return (
    <div className="p-4 bg-muted/30 space-y-4">
      {profile && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Профиль</h4>
          <div className="grid gap-1 text-sm">
            {profile.summary && (
              <p><span className="text-muted-foreground">Резюме:</span> {profile.summary}</p>
            )}
            {profile.interests.length > 0 && (
              <p><span className="text-muted-foreground">Интересы:</span> {profile.interests.join(", ")}</p>
            )}
            {profile.goals.length > 0 && (
              <p><span className="text-muted-foreground">Цели:</span> {profile.goals.join(", ")}</p>
            )}
            {profile.keywords.length > 0 && (
              <p><span className="text-muted-foreground">Ключевые слова:</span> {profile.keywords.join(", ")}</p>
            )}
            {profile.company && (
              <p><span className="text-muted-foreground">Компания:</span> {profile.company}</p>
            )}
            {profile.position && (
              <p><span className="text-muted-foreground">Должность:</span> {profile.position}</p>
            )}
            {profile.raw_text && (
              <details className="mt-1">
                <summary className="text-muted-foreground cursor-pointer text-xs">Исходный текст</summary>
                <p className="mt-1 text-xs whitespace-pre-wrap bg-muted p-2 rounded">{profile.raw_text}</p>
              </details>
            )}
          </div>
        </div>
      )}

      {business_profile && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Бизнес-профиль</h4>
          <div className="grid gap-1 text-sm">
            {business_profile.objective != null && (
              <p><span className="text-muted-foreground">Цель:</span> {String(business_profile.objective)}</p>
            )}
            {Array.isArray(business_profile.industries) && (
              <p><span className="text-muted-foreground">Индустрии:</span> {(business_profile.industries as string[]).join(", ")}</p>
            )}
            {Array.isArray(business_profile.tech_stack) && (
              <p><span className="text-muted-foreground">Стек:</span> {(business_profile.tech_stack as string[]).join(", ")}</p>
            )}
          </div>
        </div>
      )}

      {recommendations.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Рекомендации ({recommendations.length})</h4>
          <div className="space-y-1">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex items-center justify-between text-sm bg-background rounded px-2 py-1">
                <span>#{rec.rank} {rec.project_title}</span>
                <span className="text-muted-foreground text-xs">
                  {(rec.relevance_score * 100).toFixed(0)}% — {rec.category}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {contact_requests.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Запросы на контакт ({contact_requests.length})</h4>
          <div className="space-y-1">
            {contact_requests.map((cr, i) => (
              <div key={i} className="flex items-center justify-between text-sm bg-background rounded px-2 py-1">
                <span>{cr.project_title} — {cr.student_name}</span>
                <span className="text-xs text-muted-foreground">
                  {CONTACT_STATUS_LABELS[cr.status] || cr.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!profile && !business_profile && recommendations.length === 0 && contact_requests.length === 0 && (
        <p className="text-sm text-muted-foreground">Нет данных профиля</p>
      )}
    </div>
  )
}

export function GuestList() {
  const [search, setSearch] = useState("")
  const [subtypeFilter, setSubtypeFilter] = useState<string>("")
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Гости`
  }, [])

  const { data: guests, isLoading, isError } = useQuery({
    queryKey: ["guests", search, subtypeFilter],
    queryFn: () =>
      getGuests({
        ...(search ? { search } : {}),
        ...(subtypeFilter ? { subtype: subtypeFilter } : {}),
      }),
  })

  const subtypeOptions = [
    { value: "", label: "Все" },
    { value: "student", label: "Студенты" },
    { value: "applicant", label: "Абитуриенты" },
    { value: "other", label: "Другие" },
  ]

  return (
    <div className="grid gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold">
          Гости {guests && <span className="text-muted-foreground text-lg font-normal">({guests.length})</span>}
        </h2>
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Поиск по имени или Telegram..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="sm:max-w-sm"
        />
        <div className="flex gap-1">
          {subtypeOptions.map((opt) => (
            <Button
              key={opt.value}
              variant={subtypeFilter === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => setSubtypeFilter(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Загрузка...</p>}
      {isError && <p className="text-sm text-red-500">Ошибка загрузки списка гостей</p>}

      {guests && guests.length === 0 && (
        <p className="text-sm text-muted-foreground">Гости не найдены</p>
      )}

      {guests && guests.length > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Имя</th>
                    <th className="pb-2 font-medium">Telegram</th>
                    <th className="pb-2 font-medium">Тип</th>
                    <th className="pb-2 font-medium">Профиль</th>
                    <th className="pb-2 font-medium">Теги</th>
                    <th className="pb-2 font-medium text-center">Рек.</th>
                    <th className="pb-2 font-medium text-center">Контакты</th>
                  </tr>
                </thead>
                <tbody>
                  {guests.map((guest: GuestListItem) => (
                    <>
                      <tr
                        key={guest.id}
                        className="border-b last:border-0 cursor-pointer hover:bg-muted/50"
                        onClick={() => setExpandedId(expandedId === guest.id ? null : guest.id)}
                      >
                        <td className="py-2">
                          <div className="flex items-center gap-1">
                            {guest.full_name}
                            {guest.has_business_profile && (
                              <span className="px-1 py-0.5 text-[10px] bg-amber-100 text-amber-800 rounded">
                                бизнес
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 text-muted-foreground">
                          {guest.username ? `@${guest.username}` : "—"}
                        </td>
                        <td className="py-2">
                          <SubtypeBadge subtype={guest.guest_subtype} />
                        </td>
                        <td className="py-2 text-muted-foreground max-w-[200px] truncate">
                          {guest.profile_summary || "—"}
                        </td>
                        <td className="py-2">
                          <div className="flex flex-wrap gap-1">
                            {guest.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="px-1.5 py-0.5 bg-muted text-xs rounded"
                              >
                                {tag}
                              </span>
                            ))}
                            {guest.tags.length > 3 && (
                              <span className="text-xs text-muted-foreground">
                                +{guest.tags.length - 3}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 text-center">
                          {guest.recommendations_count > 0 ? (
                            <span className="px-1.5 py-0.5 bg-green-100 text-green-800 text-xs rounded">
                              {guest.recommendations_count}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-2 text-center">
                          {guest.contact_requests_count > 0 ? (
                            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                              {guest.contact_requests_count}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                      {expandedId === guest.id && (
                        <tr key={`${guest.id}-detail`}>
                          <td colSpan={7}>
                            <GuestDetailPanel guestId={guest.id} />
                          </td>
                        </tr>
                      )}
                    </>
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
