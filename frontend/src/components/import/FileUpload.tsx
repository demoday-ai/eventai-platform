import { useCallback, useState, useRef } from "react"
import { Card, CardContent } from "../ui/card"
import { Button } from "../ui/button"
import { Upload, Download, FileSpreadsheet } from "lucide-react"

interface FileUploadProps {
  accept: string
  onFileSelect: (file: File) => void
  label: string
  disabled?: boolean
  /** Accepted formats displayed as badges, e.g. ["XLSX", "CSV", "JSON"] */
  formats?: string[]
  /** Required column names */
  requiredColumns?: string[]
  /** Optional column names */
  optionalColumns?: string[]
  /** URL to download a template file */
  templateUrl?: string
}

export function FileUpload({
  accept,
  onFileSelect,
  label,
  disabled = false,
  formats,
  requiredColumns,
  optionalColumns,
  templateUrl,
}: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File) => {
      if (disabled) return
      setSelectedFile(file)
      onFileSelect(file)
    },
    [onFileSelect, disabled]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragActive(false)
      if (disabled) return
      if (e.dataTransfer.files?.[0]) {
        handleFile(e.dataTransfer.files[0])
      }
    },
    [handleFile, disabled]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) setDragActive(true)
  }, [disabled])

  const handleDragLeave = useCallback(() => {
    setDragActive(false)
  }, [])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        handleFile(e.target.files[0])
      }
    },
    [handleFile]
  )

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <Card
      className={`border-2 border-dashed transition-colors ${
        dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <CardContent className="flex flex-col items-center justify-center py-8 gap-3">
        <Upload className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{label}</p>

        {formats && formats.length > 0 && (
          <div className="flex items-center gap-1.5">
            <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
            <div className="flex gap-1">
              {formats.map((fmt) => (
                <span
                  key={fmt}
                  className="px-1.5 py-0.5 text-[11px] font-medium rounded bg-muted text-muted-foreground"
                >
                  {fmt}
                </span>
              ))}
            </div>
          </div>
        )}

        {(requiredColumns || optionalColumns) && (
          <div className="text-center text-xs text-muted-foreground space-y-0.5">
            {requiredColumns && requiredColumns.length > 0 && (
              <p>
                <span className="font-medium text-foreground">Обязательные:</span>{" "}
                {requiredColumns.map((col, i) => (
                  <span key={col}>
                    <code className="px-1 py-0.5 bg-muted rounded text-[11px]">{col}</code>
                    {i < requiredColumns.length - 1 && " "}
                  </span>
                ))}
              </p>
            )}
            {optionalColumns && optionalColumns.length > 0 && (
              <p>
                <span className="font-medium text-foreground">Опционально:</span>{" "}
                {optionalColumns.map((col, i) => (
                  <span key={col}>
                    <code className="px-1 py-0.5 bg-muted rounded text-[11px]">{col}</code>
                    {i < optionalColumns.length - 1 && " "}
                  </span>
                ))}
              </p>
            )}
          </div>
        )}

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
          >
            Выбрать файл
          </Button>
          {templateUrl && (
            <a
              href={templateUrl}
              download
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              <Download className="h-3.5 w-3.5" />
              Скачать шаблон
            </a>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />
        {selectedFile && (
          <p className="text-sm text-foreground">
            {selectedFile.name} ({formatSize(selectedFile.size)})
          </p>
        )}
      </CardContent>
    </Card>
  )
}
