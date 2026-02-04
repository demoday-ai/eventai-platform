import { useState, useEffect } from "react"
import { useMutation } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { APP_NAME } from "../lib/constants"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import {
  uploadProjects,
  uploadExperts,
  uploadGuests,
  type UploadResult,
  type ExpertUploadResult,
  type GuestUploadResult,
  type GuestUploadConflict,
  type UploadConflict,
  type ExpertUploadConflict,
} from "../lib/api-client"

export function DataImport() {
  useEffect(() => {
    document.title = `${APP_NAME} - Импорт данных`
  }, [])

  // --- Projects ---
  const [projectFile, setProjectFile] = useState<File | null>(null)
  const [projectResult, setProjectResult] = useState<UploadResult | null>(null)
  const [projectConflict, setProjectConflict] = useState<UploadConflict | null>(null)

  const projectMutation = useMutation({
    mutationFn: ({ file, replace }: { file: File; replace: boolean }) =>
      uploadProjects(file, replace),
    onSuccess: (data) => {
      setProjectResult(data)
      setProjectConflict(null)
    },
    onError: (error: AxiosError<UploadConflict>) => {
      if (error.response?.status === 409 && error.response.data) {
        setProjectConflict(error.response.data)
      }
    },
  })

  const handleProjectUpload = () => {
    if (!projectFile) return
    setProjectResult(null)
    setProjectConflict(null)
    projectMutation.mutate({ file: projectFile, replace: false })
  }

  const handleProjectReplace = () => {
    if (!projectFile) return
    setProjectConflict(null)
    projectMutation.mutate({ file: projectFile, replace: true })
  }

  // --- Experts ---
  const [expertFile, setExpertFile] = useState<File | null>(null)
  const [expertResult, setExpertResult] = useState<ExpertUploadResult | null>(null)
  const [expertConflict, setExpertConflict] = useState<ExpertUploadConflict | null>(null)

  const expertMutation = useMutation({
    mutationFn: ({ file, confirmReplace }: { file: File; confirmReplace: boolean }) =>
      uploadExperts(file, confirmReplace),
    onSuccess: (data) => {
      // Backend returns conflict info as 200 with existing_count field
      if ("existing_count" in data) {
        setExpertConflict(data as unknown as ExpertUploadConflict)
        setExpertResult(null)
      } else {
        setExpertResult(data)
        setExpertConflict(null)
      }
    },
  })

  const handleExpertUpload = () => {
    if (!expertFile) return
    setExpertResult(null)
    setExpertConflict(null)
    expertMutation.mutate({ file: expertFile, confirmReplace: false })
  }

  const handleExpertReplace = () => {
    if (!expertFile) return
    setExpertConflict(null)
    expertMutation.mutate({ file: expertFile, confirmReplace: true })
  }

  // --- Guests ---
  const [guestFile, setGuestFile] = useState<File | null>(null)
  const [guestSubtype, setGuestSubtype] = useState<string>("")
  const [guestResult, setGuestResult] = useState<GuestUploadResult | null>(null)
  const [guestConflict, setGuestConflict] = useState<GuestUploadConflict | null>(null)

  const guestMutation = useMutation({
    mutationFn: ({ file, subtype, confirmReplace }: { file: File; subtype: string; confirmReplace: boolean }) =>
      uploadGuests(file, subtype, confirmReplace),
    onSuccess: (data) => {
      if ("existing_count" in data) {
        setGuestConflict(data as unknown as GuestUploadConflict)
        setGuestResult(null)
      } else {
        setGuestResult(data)
        setGuestConflict(null)
      }
    },
  })

  const handleGuestUpload = () => {
    if (!guestFile || !guestSubtype) return
    setGuestResult(null)
    setGuestConflict(null)
    guestMutation.mutate({ file: guestFile, subtype: guestSubtype, confirmReplace: false })
  }

  const handleGuestReplace = () => {
    if (!guestFile || !guestSubtype) return
    setGuestConflict(null)
    guestMutation.mutate({ file: guestFile, subtype: guestSubtype, confirmReplace: true })
  }

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Импорт данных</h2>

      {/* Projects Section */}
      <Card>
        <CardHeader>
          <CardTitle>Проекты</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            accept=".csv,.json"
            onFileSelect={setProjectFile}
            label="Перетащите CSV или JSON файл с проектами"
          />

          <Button
            onClick={handleProjectUpload}
            disabled={!projectFile || projectMutation.isPending}
          >
            {projectMutation.isPending ? "Загрузка..." : "Загрузить"}
          </Button>

          {projectConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{projectConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleProjectReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setProjectConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {projectMutation.isError && !projectConflict && (
            <p className="text-sm text-red-500">
              Ошибка загрузки:{" "}
              {projectMutation.error instanceof Error
                ? projectMutation.error.message
                : "Неизвестная ошибка"}
            </p>
          )}

          {projectResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{projectResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {projectResult && <ImportSummary result={projectResult} type="projects" />}
        </CardContent>
      </Card>

      {/* Experts Section */}
      <Card>
        <CardHeader>
          <CardTitle>Эксперты</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            accept=".json"
            onFileSelect={setExpertFile}
            label="Перетащите JSON файл с экспертами"
          />

          <Button
            onClick={handleExpertUpload}
            disabled={!expertFile || expertMutation.isPending}
          >
            {expertMutation.isPending ? "Загрузка..." : "Загрузить"}
          </Button>

          {expertConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{expertConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleExpertReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpertConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {expertMutation.isError && (
            <p className="text-sm text-red-500">
              Ошибка загрузки:{" "}
              {expertMutation.error instanceof Error
                ? expertMutation.error.message
                : "Неизвестная ошибка"}
            </p>
          )}

          {expertResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{expertResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {expertResult && <ImportSummary result={expertResult} type="experts" />}
        </CardContent>
      </Card>

      {/* Guests Section */}
      <Card>
        <CardHeader>
          <CardTitle>Гости</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="guest-subtype" className="text-sm font-medium mb-1 block">
              Тип гостя
            </label>
            <Select value={guestSubtype} onValueChange={setGuestSubtype}>
              <SelectTrigger id="guest-subtype">
                <SelectValue placeholder="Выберите тип" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="investor">Инвестор</SelectItem>
                <SelectItem value="business_partner">Бизнес-партнёр</SelectItem>
                <SelectItem value="mentor">Ментор</SelectItem>
                <SelectItem value="hr">HR</SelectItem>
                <SelectItem value="jury">Жюри</SelectItem>
                <SelectItem value="student">Студент</SelectItem>
                <SelectItem value="applicant">Абитуриент</SelectItem>
                <SelectItem value="other">Другое</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <FileUpload
            accept=".csv,.json"
            onFileSelect={setGuestFile}
            label="Перетащите CSV или JSON файл с гостями"
          />

          <Button
            onClick={handleGuestUpload}
            disabled={!guestFile || !guestSubtype || guestMutation.isPending}
          >
            {guestMutation.isPending ? "Загрузка..." : "Загрузить"}
          </Button>

          {guestConflict && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm">{guestConflict.message}</p>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={handleGuestReplace}>
                    Заменить
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setGuestConflict(null)}
                  >
                    Отмена
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {guestMutation.isError && (
            <p className="text-sm text-red-500">
              Ошибка загрузки:{" "}
              {guestMutation.error instanceof Error
                ? guestMutation.error.message
                : "Неизвестная ошибка"}
            </p>
          )}

          {guestResult?.duplicate_warning && (
            <Card className="border-amber-400 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm text-amber-800">{guestResult.duplicate_warning}</p>
              </CardContent>
            </Card>
          )}

          {guestResult && <ImportSummary result={guestResult} type="guests" />}
        </CardContent>
      </Card>
    </div>
  )
}
