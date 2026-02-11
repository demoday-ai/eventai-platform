import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import type { MergeApplyResult } from "../../lib/api-client"

interface MergeResultProps {
  result: MergeApplyResult
  type: "projects" | "experts" | "students" | "partners"
}

const TYPE_LABELS: Record<string, string> = {
  projects: "проектов",
  experts: "экспертов",
  students: "студентов",
  partners: "партнёров",
}

export function MergeResultCard({ result, type }: MergeResultProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Результат слияния {TYPE_LABELS[type]}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Добавлено</p>
            <p className="text-2xl font-bold text-green-600">{result.added}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Обновлено</p>
            <p className="text-2xl font-bold text-blue-600">{result.updated}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Пропущено</p>
            <p className="text-2xl font-bold text-yellow-600">{result.skipped}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Ошибок</p>
            <p className="text-2xl font-bold text-red-600">{result.errors}</p>
          </div>
        </div>

        {result.error_details && result.error_details.length > 0 && (
          <div className="mt-3 border rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="px-3 py-2 text-left">Строка</th>
                  <th className="px-3 py-2 text-left">Поле</th>
                  <th className="px-3 py-2 text-left">Сообщение</th>
                </tr>
              </thead>
              <tbody>
                {result.error_details.map((err, i) => (
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
      </CardContent>
    </Card>
  )
}
