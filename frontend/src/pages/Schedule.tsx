import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { DndContext, type DragEndEvent } from "@dnd-kit/core"
import { Calendar, PanelRightOpen, PanelRightClose } from "lucide-react"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import { DayTabs } from "../components/schedule/DayTabs"
import { ScheduleTimeline } from "../components/schedule/ScheduleTimeline"
import { UnplacedPanel } from "../components/schedule/UnplacedPanel"
import { SlotPopover } from "../components/schedule/SlotPopover"
import { ScheduleToolbar } from "../components/schedule/ScheduleToolbar"
import { ConfigFromTextDialog } from "../components/schedule/ConfigFromTextDialog"
import { AddScheduleBlockDialog, type BlockSubmitData } from "../components/schedule/AddScheduleBlockDialog"
import {
  generateSchedule,
  getSchedule,
  approveSchedule,
  updateSlot,
  createSlot,
  deleteSlot,
  getUnplacedProjects,
  exportScheduleICS,
  exportScheduleXLSX,
  configureScheduleFromText,
  getCurrentClustering,
  type ScheduleSlotResponse,
  type ScheduleConfigFromTextResponse,
} from "../lib/api-client"

export function Schedule() {
  const queryClient = useQueryClient()
  const [selectedDay, setSelectedDay] = useState("")
  const [scaleMinutes, setScaleMinutes] = useState(15)
  const [editingSlot, setEditingSlot] = useState<ScheduleSlotResponse | null>(null)
  const [showApproveConfirm, setShowApproveConfirm] = useState(false)
  const [approveResult, setApproveResult] = useState<{ total_slots: number; rooms: number; days: number } | null>(null)
  const [showConfigDialog, setShowConfigDialog] = useState(false)
  const [configResult, setConfigResult] = useState<ScheduleConfigFromTextResponse | null>(null)
  const [showSidebar, setShowSidebar] = useState(true)
  const [blockDialog, setBlockDialog] = useState<{ open: boolean; type: "break" | "section" }>({ open: false, type: "break" })

  useEffect(() => {
    document.title = `${APP_NAME} - Расписание`
  }, [])

  const { data: clusteringData, isFetched: clusteringFetched } = useQuery({
    queryKey: ["clustering"],
    queryFn: () => getCurrentClustering(),
    retry: false,
  })

  const { data: scheduleData, isLoading: scheduleLoading } = useQuery({
    queryKey: ["schedule"],
    queryFn: () => getSchedule(),
    retry: false,
  })

  const { data: unplacedData, isLoading: unplacedLoading } = useQuery({
    queryKey: ["unplaced"],
    queryFn: () => getUnplacedProjects(),
    retry: false,
  })

  // Auto-select first day
  useEffect(() => {
    if (scheduleData?.days?.length && !selectedDay) {
      setSelectedDay(scheduleData.days[0].date)
    }
  }, [scheduleData, selectedDay])

  const generateMutation = useMutation({
    mutationFn: () => generateSchedule({ force: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["unplaced"] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: approveSchedule,
    onSuccess: (data) => {
      setApproveResult(data)
      setShowApproveConfirm(false)
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })

  const updateSlotMutation = useMutation({
    mutationFn: ({ slotId, body }: { slotId: string; body: Parameters<typeof updateSlot>[1] }) =>
      updateSlot(slotId, body),
    onSuccess: () => {
      setEditingSlot(null)
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["unplaced"] })
    },
  })

  const createSlotMutation = useMutation({
    mutationFn: createSlot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["unplaced"] })
    },
  })

  const deleteSlotMutation = useMutation({
    mutationFn: deleteSlot,
    onSuccess: () => {
      setEditingSlot(null)
      queryClient.invalidateQueries({ queryKey: ["schedule"] })
      queryClient.invalidateQueries({ queryKey: ["unplaced"] })
    },
  })

  const configFromTextMutation = useMutation({
    mutationFn: configureScheduleFromText,
    onSuccess: (data) => {
      setConfigResult(data)
    },
  })

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || !scheduleData) return

      const activeData = active.data.current
      const overData = over.data.current

      if (!activeData || !overData) return

      // Parse the target cell to figure out room and time
      const overId = String(over.id)
      if (!overId.startsWith("cell-")) return

      const currentDay = scheduleData.days.find((d) => d.date === selectedDay)
      if (!currentDay) return

      const colIdx = overData.col as number
      const rowIdx = overData.row as number

      const targetRoom = currentDay.rooms[colIdx - 1]
      if (!targetRoom) return

      // Compute target time from row index
      // Rows start at 2 (header = row 1). Row N = dayStart + (N - 2) * scaleMinutes
      const dayStart = computeDayStart(currentDay)
      const targetStartMs = dayStart.getTime() + (rowIdx - 2) * scaleMinutes * 60 * 1000
      const targetStart = new Date(targetStartMs)

      if (activeData.type === "unplaced-project") {
        // Drop from sidebar -> create slot
        const project = activeData.project as { id: string }
        const targetEnd = new Date(targetStartMs + scaleMinutes * 60 * 1000)
        createSlotMutation.mutate({
          room_id: targetRoom.room_id,
          start_time: targetStart.toISOString(),
          end_time: targetEnd.toISOString(),
          slot_type: "project",
          project_id: project.id,
        })
      } else if (activeData.type === "timeline-slot") {
        // Move existing slot
        const slot = activeData.slot as ScheduleSlotResponse
        const durationMs = new Date(slot.end_time).getTime() - new Date(slot.start_time).getTime()
        const targetEnd = new Date(targetStartMs + durationMs)
        updateSlotMutation.mutate({
          slotId: slot.id,
          body: {
            room_id: targetRoom.room_id,
            start_time: targetStart.toISOString(),
            end_time: targetEnd.toISOString(),
          },
        })
      }
    },
    [scheduleData, selectedDay, scaleMinutes, createSlotMutation, updateSlotMutation]
  )

  // Collect all rooms for the edit form
  const allRooms = scheduleData
    ? Array.from(
        new Map(
          scheduleData.days
            .flatMap((d) => d.rooms)
            .map((r) => [r.room_id, { id: r.room_id, name: r.room_name }])
        ).values()
      )
    : []

  const currentDayData = scheduleData?.days.find((d) => d.date === selectedDay)
  const hasSchedule = scheduleData && scheduleData.days.length > 0
  const hasNoApprovedClustering = clusteringFetched && !clusteringData?.approved_at && !hasSchedule

  if (hasNoApprovedClustering) {
    return (
      <div className="grid gap-6">
        <h2 className="text-2xl font-bold">Расписание</h2>
        <PageEmptyState
          icon={Calendar}
          title="Для генерации расписания необходима одобренная кластеризация"
          description="Одобрите кластеризацию, чтобы генерировать расписание."
          actionLabel="Перейти к кластеризации"
          actionLink="/clustering"
        />
      </div>
    )
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="grid gap-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Расписание</h2>
          <div className="flex items-center gap-2">
            {approveResult ? (
              <span className="text-sm text-green-600 font-medium">
                Одобрено: {approveResult.total_slots} слотов
              </span>
            ) : showApproveConfirm ? (
              <>
                <span className="text-sm">Вы уверены?</span>
                <Button
                  size="sm"
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                >
                  {approveMutation.isPending ? "..." : "Подтвердить"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowApproveConfirm(false)}>
                  Отмена
                </Button>
              </>
            ) : (
              <Button
                size="sm"
                onClick={() => setShowApproveConfirm(true)}
                disabled={!hasSchedule}
              >
                Одобрить
              </Button>
            )}
          </div>
        </div>

        {approveResult && (
          <div className="rounded border border-green-200 bg-green-50 p-3 text-sm">
            <p>
              Расписание одобрено: {approveResult.total_slots} слотов, {approveResult.rooms} залов, {approveResult.days} дней
            </p>
            <Link to="/messaging">
              <Button variant="outline" size="sm" className="mt-2">
                Перейти к авто-напоминаниям
              </Button>
            </Link>
          </div>
        )}

        {approveMutation.isError && (
          <p className="text-sm text-red-500">Ошибка одобрения</p>
        )}

        {/* Toolbar */}
        <ScheduleToolbar
          onAutoFill={() => generateMutation.mutate()}
          onAddBreak={() => setBlockDialog({ open: true, type: "break" })}
          onAddSection={() => setBlockDialog({ open: true, type: "section" })}
          onExportICS={() => exportScheduleICS()}
          onExportXLSX={() => exportScheduleXLSX()}
          onConfigFromText={() => {
            setConfigResult(null)
            setShowConfigDialog(true)
          }}
          isGenerating={generateMutation.isPending}
          scaleMinutes={scaleMinutes}
          onScaleChange={setScaleMinutes}
        />

        {generateMutation.isError && (
          <p className="text-sm text-red-500">
            Ошибка: {generateMutation.error instanceof Error ? generateMutation.error.message : "Неизвестная ошибка"}
          </p>
        )}

        {/* Day tabs */}
        {hasSchedule && (
          <DayTabs
            days={scheduleData.days}
            selectedDay={selectedDay}
            onDayChange={setSelectedDay}
          />
        )}

        {/* Main content */}
        {scheduleLoading ? (
          <div className="text-center py-12 text-muted-foreground">Загрузка расписания...</div>
        ) : !hasSchedule ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">
              Расписание пусто. Используйте "Авто-заполнить" или "AI-конфигурация" для начала.
            </p>
          </div>
        ) : (
          <div className="flex gap-3">
            {/* Timeline */}
            <div className="flex-1 min-w-0">
              {currentDayData && (
                <ScheduleTimeline
                  rooms={currentDayData.rooms}
                  dayDate={currentDayData.date}
                  scaleMinutes={scaleMinutes}
                  onSlotClick={(slot) => setEditingSlot(slot)}
                />
              )}
            </div>

            {/* Sidebar toggle (mobile) */}
            <button
              className="fixed bottom-4 right-4 z-40 md:hidden rounded-full bg-primary text-primary-foreground p-3 shadow-lg"
              onClick={() => setShowSidebar(!showSidebar)}
              aria-label="Переключить панель"
            >
              {showSidebar ? <PanelRightClose className="h-5 w-5" /> : <PanelRightOpen className="h-5 w-5" />}
            </button>

            {/* Unplaced panel */}
            <div
              className={`w-[280px] flex-shrink-0 border rounded-lg bg-white ${
                showSidebar ? "block" : "hidden"
              } md:block`}
            >
              <UnplacedPanel
                items={unplacedData?.items || []}
                total={unplacedData?.total || 0}
                isLoading={unplacedLoading}
              />
            </div>
          </div>
        )}
      </div>

      {/* Slot edit popover */}
      {editingSlot && (
        <SlotPopover
          slot={editingSlot}
          rooms={allRooms}
          onSave={(slotId, body) => updateSlotMutation.mutate({ slotId, body })}
          onDelete={(slotId) => deleteSlotMutation.mutate(slotId)}
          onClose={() => setEditingSlot(null)}
          isSaving={updateSlotMutation.isPending}
        />
      )}

      {/* Config from text dialog */}
      <ConfigFromTextDialog
        open={showConfigDialog}
        onClose={() => setShowConfigDialog(false)}
        onSubmit={(text) => configFromTextMutation.mutate({ text })}
        onAccept={() => {
          setShowConfigDialog(false)
          // After config accepted, auto-fill
          generateMutation.mutate()
        }}
        isParsing={configFromTextMutation.isPending}
        parseResult={configResult}
      />

      {/* Add break/section dialog */}
      <AddScheduleBlockDialog
        open={blockDialog.open}
        onClose={() => setBlockDialog({ ...blockDialog, open: false })}
        onSubmit={(data: BlockSubmitData) => {
          createSlotMutation.mutate({
            room_id: data.room_id,
            start_time: data.start_time,
            end_time: data.end_time,
            slot_type: data.slot_type,
            title: data.title,
          })
          setBlockDialog({ ...blockDialog, open: false })
        }}
        blockType={blockDialog.type}
        rooms={allRooms}
        selectedDay={selectedDay}
      />
    </DndContext>
  )
}

/** Compute day start from the earliest slot or default to 10:00 */
function computeDayStart(dayData: { date: string; rooms: { slots: { start_time: string }[] }[] }): Date {
  let earliest = new Date(`${dayData.date}T10:00:00`)
  for (const room of dayData.rooms) {
    for (const slot of room.slots) {
      const s = new Date(slot.start_time)
      if (s < earliest) earliest = s
    }
  }
  earliest.setMinutes(Math.floor(earliest.getMinutes() / 15) * 15, 0, 0)
  return earliest
}
