import { useState } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { Button } from "../ui/button"
import type { MergePreview } from "../../lib/api-client"

interface MergePreviewCardProps {
  preview: MergePreview
  type: "projects" | "experts" | "students" | "partners"
  onApply: (addNew: boolean, updateExisting: boolean) => void
  onReplaceAll: () => void
  onCancel: () => void
  isApplying?: boolean
}

const TYPE_LABELS: Record<string, string> = {
  projects: "проектов",
  experts: "экспертов",
  students: "студентов",
  partners: "партнёров",
}

export function MergePreviewCard({
  preview,
  type,
  onApply,
  onReplaceAll,
  onCancel,
  isApplying = false,
}: MergePreviewCardProps) {
  const [addNew, setAddNew] = useState(true)
  const [updateExisting, setUpdateExisting] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [showUpdated, setShowUpdated] = useState(false)
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false)

  const hasChanges = preview.new_count > 0 || preview.updated_count > 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Результат анализа файла</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Новых</p>
            <p className="text-2xl font-bold text-green-600">{preview.new_count}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Обновлённых</p>
            <p className="text-2xl font-bold text-blue-600">{preview.updated_count}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Дубликатов</p>
            <p className="text-2xl font-bold text-yellow-600">{preview.duplicate_count}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Ошибок</p>
            <p className="text-2xl font-bold text-red-600">{preview.error_count}</p>
          </div>
        </div>

        {/* New items (collapsible) */}
        {preview.new_count > 0 && (
          <div>
            <button
              className="flex items-center gap-1 text-sm font-medium text-foreground hover:underline"
              onClick={() => setShowNew(!showNew)}
            >
              <span>{showNew ? "\u25BE" : "\u25B8"}</span>
              Новые записи ({preview.new_count})
            </button>
            {showNew && (
              <ul className="mt-1 ml-4 space-y-0.5 text-sm text-muted-foreground">
                {preview.new_items.map((item, i) => (
                  <li key={i}>
                    {item.name}
                    {item.telegram && (
                      <span className="ml-1 text-xs">(@{item.telegram})</span>
                    )}
                  </li>
                ))}
                {preview.new_count > preview.new_items.length && (
                  <li className="text-xs italic">
                    ...и ещё {preview.new_count - preview.new_items.length}
                  </li>
                )}
              </ul>
            )}
          </div>
        )}

        {/* Updated items (collapsible) */}
        {preview.updated_count > 0 && (
          <div>
            <button
              className="flex items-center gap-1 text-sm font-medium text-foreground hover:underline"
              onClick={() => setShowUpdated(!showUpdated)}
            >
              <span>{showUpdated ? "\u25BE" : "\u25B8"}</span>
              Изменённые записи ({preview.updated_count})
            </button>
            {showUpdated && (
              <ul className="mt-1 ml-4 space-y-2 text-sm">
                {preview.updated_items.map((item, i) => (
                  <li key={i}>
                    <span className="font-medium">{item.name}</span>
                    <ul className="ml-3 text-xs text-muted-foreground">
                      {item.changed_fields.map((cf, j) => (
                        <li key={j}>
                          {cf.field}:{" "}
                          <span className="text-red-500 line-through">{cf.old_value || "—"}</span>
                          {" \u2192 "}
                          <span className="text-green-600">{cf.new_value || "—"}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Project tag stats */}
        {type === "projects" && preview.with_tags_in_db !== null && (
          <p className="text-sm text-muted-foreground">
            {preview.with_tags_in_db} {TYPE_LABELS[type]} с тегами,{" "}
            {preview.missing_tags_in_db} без тегов (в БД)
          </p>
        )}

        {/* Errors */}
        {preview.error_count > 0 && preview.errors.length > 0 && (
          <div className="border rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="px-3 py-2 text-left">Строка</th>
                  <th className="px-3 py-2 text-left">Поле</th>
                  <th className="px-3 py-2 text-left">Сообщение</th>
                </tr>
              </thead>
              <tbody>
                {preview.errors.map((err, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-3 py-2">{err.row}</td>
                    <td className="px-3 py-2">{err.field}</td>
                    <td className="px-3 py-2">{err.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Checkboxes + actions */}
        {hasChanges && (
          <div className="space-y-3 pt-2 border-t">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={addNew}
                onChange={(e) => setAddNew(e.target.checked)}
                disabled={preview.new_count === 0}
              />
              Добавить новых ({preview.new_count})
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={updateExisting}
                onChange={(e) => setUpdateExisting(e.target.checked)}
                disabled={preview.updated_count === 0}
              />
              Обновить изменённых ({preview.updated_count})
            </label>
            <p className="text-xs text-muted-foreground">
              Дубликаты ({preview.duplicate_count}) будут пропущены
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 pt-2">
          {hasChanges && (
            <Button
              onClick={() => onApply(addNew, updateExisting)}
              disabled={isApplying || (!addNew && !updateExisting)}
            >
              {isApplying ? "Применение..." : "Применить"}
            </Button>
          )}
          {!showReplaceConfirm ? (
            <Button
              variant="outline"
              onClick={() => setShowReplaceConfirm(true)}
              disabled={isApplying}
            >
              Заменить всё
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-sm text-destructive font-medium">Удалить все данные и загрузить заново?</span>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setShowReplaceConfirm(false)
                  onReplaceAll()
                }}
                disabled={isApplying}
              >
                Да, заменить
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowReplaceConfirm(false)}
              >
                Нет
              </Button>
            </div>
          )}
          <Button variant="ghost" onClick={onCancel} disabled={isApplying}>
            Отмена
          </Button>
        </div>

        {/* No changes message */}
        {!hasChanges && preview.duplicate_count > 0 && (
          <p className="text-sm text-muted-foreground">
            Все записи файла уже есть в базе. Изменений не требуется.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
