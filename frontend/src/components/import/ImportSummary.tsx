import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import type { UploadResult, ExpertUploadResult, GuestUploadResult } from "../../lib/api-client"

interface ImportSummaryProps {
  result: UploadResult | ExpertUploadResult | GuestUploadResult
  type: "projects" | "experts" | "guests" | "students" | "partners"
}

function isUploadResult(result: UploadResult | ExpertUploadResult | GuestUploadResult): result is UploadResult {
  return "loaded" in result && !("imported" in result) && !("with_tags" in result)
}

function isGuestUploadResult(result: UploadResult | ExpertUploadResult | GuestUploadResult): result is GuestUploadResult {
  return "imported" in result && "total_parsed" in result && !("with_tags" in result)
}

export function ImportSummary({ result, type }: ImportSummaryProps) {
  if (type === "projects" && isUploadResult(result)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Результат импорта проектов</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Загружено</p>
              <p className="text-2xl font-bold text-green-600">{result.loaded}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Ошибок</p>
              <p className="text-2xl font-bold text-red-600">{result.errors}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Дубликатов</p>
              <p className="text-2xl font-bold text-yellow-600">{result.duplicates}</p>
            </div>
          </div>

          {result.error_details.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Ошибки:</p>
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
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  // Guest/Student/Partner upload result
  const guestLabel = type === "students" ? "студентов" : type === "partners" ? "партнёров" : "гостей"
  if ((type === "guests" || type === "students" || type === "partners") && isGuestUploadResult(result)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Результат импорта {guestLabel}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Обработано</p>
              <p className="text-2xl font-bold">{result.total_parsed}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Импортировано</p>
              <p className="text-2xl font-bold text-green-600">{result.imported}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Дубликатов</p>
              <p className="text-2xl font-bold text-yellow-600">{result.duplicates}</p>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Ошибки:</p>
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
                    {result.errors.map((err, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-3 py-2">{err.row}</td>
                        <td className="px-3 py-2">{err.field}</td>
                        <td className="px-3 py-2">{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  // Expert upload result
  const expertResult = result as ExpertUploadResult
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Результат импорта экспертов</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Обработано</p>
            <p className="text-2xl font-bold">{expertResult.total_parsed}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Импортировано</p>
            <p className="text-2xl font-bold text-green-600">{expertResult.imported}</p>
          </div>
          <div>
            <p className="text-muted-foreground">С тегами</p>
            <p className="text-2xl font-bold text-blue-600">{expertResult.with_tags}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Без тегов</p>
            <p className="text-2xl font-bold text-yellow-600">{expertResult.without_tags}</p>
          </div>
        </div>

        {expertResult.errors.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Ошибки:</p>
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
                  {expertResult.errors.map((err, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-2">{err.row}</td>
                      <td className="px-3 py-2">{err.field}</td>
                      <td className="px-3 py-2">{err.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
