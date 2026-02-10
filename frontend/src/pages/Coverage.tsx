import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { StatusBadge } from "../components/shared/StatusBadge"
import {
  getCoverageSummary,
  getCoverageGaps,
  getEscalations,
  resolveEscalation,
} from "../lib/api-client"

const TABS = ["Обзор", "Пробелы", "Эскалации"] as const
type Tab = (typeof TABS)[number]

export function CoverageTab() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>("Обзор")
  const [escalationFilter, setEscalationFilter] = useState<"open" | "all">("open")

  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
    queryKey: ["coverageSummary"],
    queryFn: getCoverageSummary,
    refetchInterval: 60000,
  })

  const { data: gaps, isLoading: gapsLoading } = useQuery({
    queryKey: ["coverageGaps"],
    queryFn: getCoverageGaps,
    enabled: activeTab === "Пробелы",
  })

  const { data: escalations, isLoading: escalationsLoading } = useQuery({
    queryKey: ["escalations", escalationFilter],
    queryFn: () => getEscalations(escalationFilter === "open" ? false : undefined),
    enabled: activeTab === "Эскалации",
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => resolveEscalation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["escalations"] })
    },
  })

  return (
    <div className="grid gap-6">
      {/* Sub-tab buttons */}
      <div className="flex gap-1 border-b pb-0 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors whitespace-nowrap ${
              activeTab === tab
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab: Обзор */}
      {activeTab === "Обзор" && (
        <div className="space-y-4">
          {summaryLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {summaryError && <p className="text-sm text-red-500">Ошибка загрузки данных покрытия</p>}
          {summary && (
            <>
              <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.totals.confirmed}</div>
                    <p className="text-sm text-muted-foreground">Подтверждено</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.totals.pending}</div>
                    <p className="text-sm text-muted-foreground">Ожидает</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.totals.declined}</div>
                    <p className="text-sm text-muted-foreground">Отклонено</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{summary.totals.coverage_percent}%</div>
                    <p className="text-sm text-muted-foreground">Покрытие</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Залы</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left">
                          <th className="py-2 pr-4">Зал</th>
                          <th className="py-2 pr-4">Проектов</th>
                          <th className="py-2 pr-4">Теги</th>
                          <th className="py-2 pr-4">Подтв.</th>
                          <th className="py-2 pr-4">Ожид.</th>
                          <th className="py-2 pr-4">Откл.</th>
                          <th className="py-2 pr-4">Уровень</th>
                          <th className="py-2"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.rooms.map((room) => (
                          <tr key={room.room_id} className="border-b">
                            <td className="py-2 pr-4 font-medium">{room.room_name}</td>
                            <td className="py-2 pr-4">{room.project_count}</td>
                            <td className="py-2 pr-4">
                              <span className="text-xs text-muted-foreground">
                                {room.top_tags.slice(0, 3).join(", ")}
                              </span>
                            </td>
                            <td className="py-2 pr-4">{room.confirmed}</td>
                            <td className="py-2 pr-4">{room.pending}</td>
                            <td className="py-2 pr-4">{room.declined}</td>
                            <td className="py-2 pr-4"><StatusBadge status={room.coverage_level} variant="coverage" /></td>
                            <td className="py-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => navigate(`/experts/rooms/${room.room_id}`)}
                              >
                                Детали
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      {/* Tab: Пробелы */}
      {activeTab === "Пробелы" && (
        <div className="space-y-4">
          {gapsLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {gaps && (
            <>
              <p className="text-sm text-muted-foreground">
                Всего пробелов: <span className="font-semibold text-foreground">{gaps.total_gaps}</span>
              </p>
              {gaps.gaps.length === 0 ? (
                <p className="text-muted-foreground">Пробелов не обнаружено</p>
              ) : (
                gaps.gaps.map((gap, idx) => (
                  <GapCard key={`${gap.room_id}-${gap.uncovered_tag}-${idx}`} gap={gap} />
                ))
              )}
            </>
          )}
        </div>
      )}

      {/* Tab: Эскалации */}
      {activeTab === "Эскалации" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant={escalationFilter === "open" ? "default" : "outline"}
              size="sm"
              onClick={() => setEscalationFilter("open")}
            >
              Открытые
            </Button>
            <Button
              variant={escalationFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setEscalationFilter("all")}
            >
              Все
            </Button>
          </div>
          {escalationsLoading && <p className="text-muted-foreground">Загрузка...</p>}
          {escalations && escalations.length === 0 && (
            <p className="text-muted-foreground">Нет эскалаций</p>
          )}
          {escalations && escalations.length > 0 && (
            <Card>
              <CardContent className="pt-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="py-2 pr-4">Тип</th>
                        <th className="py-2 pr-4">Эксперт</th>
                        <th className="py-2 pr-4">Зал</th>
                        <th className="py-2 pr-4">Сообщение</th>
                        <th className="py-2 pr-4">Дата</th>
                        <th className="py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {escalations.map((esc) => (
                        <tr key={esc.id} className="border-b">
                          <td className="py-2 pr-4">{esc.type}</td>
                          <td className="py-2 pr-4">{esc.expert_name}</td>
                          <td className="py-2 pr-4">{esc.room_name}</td>
                          <td className="py-2 pr-4 max-w-xs truncate">{esc.message}</td>
                          <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(esc.created_at).toLocaleString("ru-RU")}
                          </td>
                          <td className="py-2">
                            {!esc.resolved && (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={resolveMutation.isPending}
                                onClick={() => resolveMutation.mutate(esc.id)}
                              >
                                Решить
                              </Button>
                            )}
                            {esc.resolved && (
                              <span className="text-xs text-green-600">Решено</span>
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
      )}
    </div>
  )
}

function GapCard({ gap }: { gap: import("../lib/api-client").CoverageGap }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card>
      <CardContent className="pt-6 space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-medium">{gap.room_name}</span>
            <span className="mx-2 text-muted-foreground">·</span>
            <span className="text-sm">Тег: <span className="font-medium">{gap.uncovered_tag}</span></span>
            <span className="mx-2 text-muted-foreground">·</span>
            <span className="text-sm text-muted-foreground">{gap.project_count_with_tag} проектов</span>
          </div>
          {gap.candidates.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => setExpanded(!expanded)}>
              {expanded ? "Скрыть" : `Кандидаты (${gap.candidates.length})`}
            </Button>
          )}
        </div>
        {expanded && gap.candidates.length > 0 && (
          <div className="mt-2 space-y-1">
            {gap.candidates.map((c) => (
              <div key={c.expert_id} className="text-sm flex items-center gap-2 pl-4">
                <span className="font-medium">{c.name}</span>
                <span className="text-xs text-muted-foreground">
                  теги: {c.matching_tags.join(", ")}
                </span>
                {c.current_rooms.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    (залы: {c.current_rooms.join(", ")})
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
