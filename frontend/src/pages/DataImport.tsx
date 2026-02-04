import { useState, useEffect } from "react"
import { useMutation } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { FileUpload } from "../components/import/FileUpload"
import { ImportSummary } from "../components/import/ImportSummary"
import { APP_NAME } from "../lib/constants"
import {
  uploadProjects,
  uploadExperts,
  type UploadResult,
  type ExpertUploadResult,
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

          {expertResult && <ImportSummary result={expertResult} type="experts" />}
        </CardContent>
      </Card>
    </div>
  )
}
