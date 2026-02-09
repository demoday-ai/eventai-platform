import React, { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Users, UserSearch, Send, X } from "lucide-react"
import { Card, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import {
  getGuests,
  getGuestDetail,
  isNoEventError,
  type GuestListItem,
  type GuestDetailResponse,
} from "../lib/api-client"

const ROLE_LABELS: Record<string, string> = {
  guest: "Гость",
  business: "Партнёр",
}

const ROLE_STYLES: Record<string, string> = {
  guest: "bg-blue-100 text-blue-800",
  business: "bg-amber-100 text-amber-800",
}

const SUBTYPE_LABELS: Record<string, string> = {
  student: "Студент",
  applicant: "Абитуриент",
  other: "Другой",
}

const CONTACT_STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает",
  approved: "Одобрен",
  rejected: "Отклонён",
  expired: "Истёк",
}

function RoleBadge({ role, subtype }: { role: string; subtype: string | null }) {
  const style = ROLE_STYLES[role] || "bg-gray-100 text-gray-700"
  let label = ROLE_LABELS[role] || role
  if (role === "guest" && subtype) {
    label = SUBTYPE_LABELS[subtype] || subtype
  }
  return (
    <span className={`px-1.5 py-0.5 text-xs rounded ${style}`}>
      {label}
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
            {Array.isArray(business_profile.project_stages) && (
              <p><span className="text-muted-foreground">Стадии:</span> {(business_profile.project_stages as string[]).join(", ")}</p>
            )}
            {business_profile.collaboration_format != null && (
              <p><span className="text-muted-foreground">Формат:</span> {String(business_profile.collaboration_format)}</p>
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

const ACTIVITY_FILTERS = [
  { value: "has_recommendations", label: "С рекомендациями" },
  { value: "has_business_profile", label: "С бизнес-профилем" },
  { value: "has_contacts", label: "С запросами контактов" },
] as const

type ActivityFilterValue = typeof ACTIVITY_FILTERS[number]["value"]

export function GuestList() {
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState<string>("")
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [activityFilters, setActivityFilters] = useState<ActivityFilterValue[]>([])

  useEffect(() => {
    document.title = `${APP_NAME} - Гости и партнёры`
  }, [])

  const { data: guests, isLoading, isError, error } = useQuery({
    queryKey: ["guests", search, roleFilter],
    queryFn: () =>
      getGuests({
        ...(search ? { search } : {}),
        ...(roleFilter ? { role: roleFilter } : {}),
      }),
  })

  const availableTags = useMemo(() => {
    if (!guests) return []
    const tagSet = new Set<string>()
    guests.forEach((g) => g.tags.forEach((t) => tagSet.add(t)))
    return Array.from(tagSet).sort()
  }, [guests])

  const filteredGuests = useMemo(() => {
    if (!guests) return undefined
    return guests.filter((g) => {
      if (selectedTags.length > 0 && !selectedTags.some((t) => g.tags.includes(t))) return false
      for (const af of activityFilters) {
        if (af === "has_recommendations" && g.recommendations_count === 0) return false
        if (af === "has_business_profile" && !g.has_business_profile) return false
        if (af === "has_contacts" && g.contact_requests_count === 0) return false
      }
      return true
    })
  }, [guests, selectedTags, activityFilters])

  const hasAdvancedFilters = selectedTags.length > 0 || activityFilters.length > 0
  const activeFilterCount = selectedTags.length + activityFilters.length + (roleFilter ? 1 : 0) + (search ? 1 : 0)

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  const toggleActivity = (value: ActivityFilterValue) => {
    setActivityFilters((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    )
  }

  const resetAllFilters = () => {
    setSearch("")
    setRoleFilter("")
    setSelectedTags([])
    setActivityFilters([])
  }

  const segmentParams = new URLSearchParams()
  if (roleFilter) segmentParams.set("segment_role", roleFilter)
  if (selectedTags.length > 0) segmentParams.set("segment_tags", selectedTags.join(","))

  const filterOptions = [
    { value: "", label: "Все" },
    { value: "business", label: "Партнёры" },
    { value: "guest", label: "Гости" },
  ]

  return (
    <div className="grid gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold">
          Гости и партнёры {filteredGuests && <span className="text-muted-foreground text-lg font-normal">({filteredGuests.length}{guests && filteredGuests.length !== guests.length ? ` из ${guests.length}` : ""})</span>}
        </h2>
        {hasAdvancedFilters && filteredGuests && filteredGuests.length > 0 && (
          <Link to={`/messaging?${segmentParams.toString()}`}>
            <Button variant="outline" size="sm">
              <Send className="h-4 w-4 mr-1" />
              Отправить сегменту
            </Button>
          </Link>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row gap-2">
          <Input
            placeholder="Поиск по имени или Telegram..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="sm:max-w-sm"
          />
          <div className="flex gap-1">
            {filterOptions.map((opt) => (
              <Button
                key={opt.value}
                variant={roleFilter === opt.value ? "default" : "outline"}
                size="sm"
                onClick={() => setRoleFilter(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>

        {availableTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5" data-testid="tag-filters">
            {availableTags.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
                  selectedTags.includes(tag)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted text-muted-foreground border-transparent hover:border-border"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {ACTIVITY_FILTERS.map((af) => (
            <button
              key={af.value}
              type="button"
              onClick={() => toggleActivity(af.value)}
              className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                activityFilters.includes(af.value)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-muted text-muted-foreground border-transparent hover:border-border"
              }`}
            >
              {af.label}
            </button>
          ))}

          {activeFilterCount > 0 && (
            <Button variant="ghost" size="sm" onClick={resetAllFilters} className="h-6 px-2 text-xs">
              <X className="h-3 w-3 mr-1" />
              Сбросить ({activeFilterCount})
            </Button>
          )}
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Загрузка...</p>}
      {isError && isNoEventError(error) && (
        <PageEmptyState
          icon={Users}
          title="Создайте мероприятие"
          description="Создайте мероприятие на странице Импорта, чтобы начать работу с аудиторией."
          actionLabel="Перейти к импорту"
          actionLink="/import"
        />
      )}
      {isError && !isNoEventError(error) && <p className="text-sm text-red-500">Ошибка загрузки списка гостей</p>}

      {filteredGuests && filteredGuests.length === 0 && !search && !roleFilter && !hasAdvancedFilters && (
        <PageEmptyState
          icon={UserSearch}
          title="Пока никто не взаимодействовал с ботом"
          description="Контакты появятся автоматически, когда участники начнут использовать бота."
        />
      )}
      {filteredGuests && filteredGuests.length === 0 && (search || roleFilter || hasAdvancedFilters) && (
        <p className="text-sm text-muted-foreground">Гости не найдены</p>
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
                    <th className="pb-2 font-medium">Роль</th>
                    <th className="pb-2 font-medium">Профиль</th>
                    <th className="pb-2 font-medium">Теги</th>
                    <th className="pb-2 font-medium text-center">Рек.</th>
                    <th className="pb-2 font-medium text-center">Контакты</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGuests.map((guest: GuestListItem) => (
                    <React.Fragment key={guest.id}>
                      <tr
                        className="border-b last:border-0 cursor-pointer hover:bg-muted/50"
                        onClick={() => setExpandedId(expandedId === guest.id ? null : guest.id)}
                      >
                        <td className="py-2">{guest.full_name}</td>
                        <td className="py-2 text-muted-foreground">
                          {guest.username ? `@${guest.username}` : "—"}
                        </td>
                        <td className="py-2">
                          <RoleBadge role={guest.role} subtype={guest.guest_subtype} />
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
                        <tr>
                          <td colSpan={7}>
                            <GuestDetailPanel guestId={guest.id} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
