import { useState } from "react"
import { useDraggable } from "@dnd-kit/core"
import { Input } from "../ui/input"
import { cn } from "../../lib/utils"
import type { UnplacedProject } from "../../lib/api-client"

interface UnplacedPanelProps {
  items: UnplacedProject[]
  total: number
  isLoading: boolean
}

interface DraggableProjectCardProps {
  project: UnplacedProject
}

function DraggableProjectCard({ project }: DraggableProjectCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `unplaced-${project.id}`,
    data: { type: "unplaced-project", project },
  })

  const style: React.CSSProperties = transform
    ? { transform: `translate(${transform.x}px, ${transform.y}px)`, zIndex: 50 }
    : {}

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "rounded border border-blue-200 bg-blue-50 px-2 py-1.5 text-xs cursor-grab",
        "hover:border-blue-400 hover:shadow-sm",
        isDragging && "opacity-50 shadow-lg"
      )}
      {...listeners}
      {...attributes}
    >
      <div className="font-medium truncate">{project.title}</div>
      <div className="text-[10px] text-muted-foreground truncate">{project.author}</div>
      {project.tags.length > 0 && (
        <div className="flex flex-wrap gap-0.5 mt-1">
          {project.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="rounded bg-blue-100 px-1 text-[9px]">{tag}</span>
          ))}
          {project.tags.length > 3 && (
            <span className="text-[9px] text-muted-foreground">+{project.tags.length - 3}</span>
          )}
        </div>
      )}
    </div>
  )
}

export function UnplacedPanel({ items, total, isLoading }: UnplacedPanelProps) {
  const [search, setSearch] = useState("")

  const filtered = search
    ? items.filter(
        (p) =>
          p.title.toLowerCase().includes(search.toLowerCase()) ||
          p.author.toLowerCase().includes(search.toLowerCase()) ||
          p.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
      )
    : items

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <h3 className="text-sm font-medium">
          Нераспределённые
        </h3>
        <span className="text-xs text-muted-foreground">
          {filtered.length} из {total}
        </span>
      </div>
      <div className="px-3 py-2 border-b">
        <Input
          placeholder="Поиск..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-7 text-xs"
        />
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {isLoading ? (
          <p className="text-xs text-muted-foreground text-center py-4">Загрузка...</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">
            {total === 0 ? "Все проекты распределены" : "Ничего не найдено"}
          </p>
        ) : (
          filtered.map((project) => (
            <DraggableProjectCard key={project.id} project={project} />
          ))
        )}
      </div>
    </div>
  )
}
