import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { MessageCircle } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import {
  getSupportThreads,
  getSupportMessages,
  sendSupportReply,
  closeSupportThread,
} from "../lib/api-client"

export function SupportChat() {
  const queryClient = useQueryClient()
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [draftMessage, setDraftMessage] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("open")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    document.title = `${APP_NAME} - Чат поддержки`
  }, [])

  const { data: threadList, isLoading } = useQuery({
    queryKey: ["support-threads", statusFilter],
    queryFn: () => getSupportThreads({ status: statusFilter || undefined }),
    refetchInterval: 3000,
  })

  const { data: messages } = useQuery({
    queryKey: ["support-messages", selectedThreadId],
    queryFn: () => getSupportMessages(selectedThreadId!),
    enabled: !!selectedThreadId,
    refetchInterval: 3000,
  })

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const sendMutation = useMutation({
    mutationFn: () => sendSupportReply(selectedThreadId!, draftMessage),
    onSuccess: () => {
      setDraftMessage("")
      queryClient.invalidateQueries({ queryKey: ["support-messages", selectedThreadId] })
      queryClient.invalidateQueries({ queryKey: ["support-threads"] })
    },
  })

  const closeMutation = useMutation({
    mutationFn: () => closeSupportThread(selectedThreadId!),
    onSuccess: () => {
      setSelectedThreadId(null)
      queryClient.invalidateQueries({ queryKey: ["support-threads"] })
    },
  })

  const threads = threadList?.threads ?? []
  const selectedThread = threads.find((t) => t.id === selectedThreadId)

  return (
    <div className="grid gap-4 h-[calc(100vh-12rem)]" style={{ gridTemplateColumns: "350px 1fr" }}>
      {/* Thread list */}
      <Card className="overflow-hidden flex flex-col">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Диалоги</CardTitle>
            <select
              className="rounded border px-2 py-1 text-xs"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setSelectedThreadId(null) }}
            >
              <option value="open">Открытые</option>
              <option value="closed">Закрытые</option>
              <option value="">Все</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground p-4">Загрузка...</p>
          ) : threads.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4">Нет диалогов</p>
          ) : (
            <div className="divide-y">
              {threads.map((thread) => (
                <button
                  key={thread.id}
                  className={`w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors ${
                    thread.id === selectedThreadId ? "bg-muted" : ""
                  }`}
                  onClick={() => setSelectedThreadId(thread.id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm truncate">
                      {thread.user_name}
                    </span>
                    {thread.unread && (
                      <span className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {thread.user_role || "пользователь"} - {thread.message_count} сообщ.
                  </p>
                  {thread.last_message && (
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {thread.last_message}
                    </p>
                  )}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chat panel */}
      <Card className="overflow-hidden flex flex-col">
        {selectedThread ? (
          <>
            <CardHeader className="pb-2 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">{selectedThread.user_name}</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    @{selectedThread.user_username || "N/A"} - {selectedThread.user_role || "пользователь"}
                    {selectedThread.status === "closed" && " (закрыт)"}
                  </p>
                </div>
                {selectedThread.status === "open" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => closeMutation.mutate()}
                    disabled={closeMutation.isPending}
                  >
                    Закрыть диалог
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages?.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender_type === "organizer" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                      msg.sender_type === "organizer"
                        ? "bg-blue-500 text-white"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-xs opacity-70 mb-0.5">{msg.sender_name}</p>
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                    <p className="text-[10px] opacity-50 mt-1">
                      {new Date(msg.created_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </CardContent>
            {selectedThread.status === "open" && (
              <div className="border-t p-3 flex gap-2">
                <input
                  className="flex-1 rounded border px-3 py-2 text-sm"
                  value={draftMessage}
                  onChange={(e) => setDraftMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && draftMessage.trim()) {
                      e.preventDefault()
                      sendMutation.mutate()
                    }
                  }}
                  placeholder="Написать ответ..."
                  disabled={sendMutation.isPending}
                />
                <Button
                  onClick={() => sendMutation.mutate()}
                  disabled={!draftMessage.trim() || sendMutation.isPending}
                >
                  Отправить
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <PageEmptyState
              icon={MessageCircle}
              title="Выберите диалог"
              description="Выберите диалог из списка слева для просмотра и ответа"
            />
          </div>
        )}
      </Card>
    </div>
  )
}
