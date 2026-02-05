import { useCallback, useState, useRef } from "react"
import { Card, CardContent } from "../ui/card"
import { Button } from "../ui/button"
import { Upload } from "lucide-react"

interface FileUploadProps {
  accept: string
  onFileSelect: (file: File) => void
  label: string
  disabled?: boolean
}

export function FileUpload({ accept, onFileSelect, label, disabled = false }: FileUploadProps) {
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
        <Button
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          Выбрать файл
        </Button>
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
