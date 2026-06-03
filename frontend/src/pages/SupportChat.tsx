import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { MessageCircle } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { PageEmptyState } from "../components/ui/PageEmptyState"
import { APP_NAME } from "../lib/constants"
import {
  getConversations,
  getConversationMessages,
  replyToConversation,
  releaseConversation,
  closeConversation,
} from "../lib/api-client"

export function SupportChat() {
  const queryClient = useQueryClient()
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [draftMessage, setDraftMessage] = useState("")
  const [filter, setFilter] = useState<string>("all")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevMsgCountRef = useRef(0)

  useEffect(() => {
    document.title = `${APP_NAME} - Чаты`
  }, [])

  const { data: convList, isLoading } = useQuery({
    queryKey: ["conversations", filter],
    queryFn: () => getConversations({ filter }),
    refetchInterval: 3000,
  })

  const [sendError, setSendError] = useState<string | null>(null)

  const { data: messages, isError: messagesError } = useQuery({
    queryKey: ["conversation-messages", selectedUserId],
    queryFn: () => getConversationMessages(selectedUserId!),
    enabled: !!selectedUserId,
    refetchInterval: 3000,
  })

  // Reset scroll baseline when switching conversations.
  useEffect(() => {
    prevMsgCountRef.current = 0
  }, [selectedUserId])

  // Auto-scroll only when the message count actually grows (the 3s refetch
  // returns a fresh array each time; scrolling on every refetch would yank
  // the view down and block reading history).
  useEffect(() => {
    const count = messages?.length ?? 0
    if (count > prevMsgCountRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
    prevMsgCountRef.current = count
  }, [messages])

  const sendMutation = useMutation({
    mutationFn: ({ userId, text }: { userId: string; text: string }) =>
      replyToConversation(userId, text),
    onSuccess: (_, { userId }) => {
      setDraftMessage("")
      setSendError(null)
      queryClient.invalidateQueries({ queryKey: ["conversation-messages", userId] })
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
    onError: (err) => setSendError(err instanceof Error ? err.message : "Ошибка отправки"),
  })

  const releaseMutation = useMutation({
    mutationFn: ({ userId }: { userId: string }) => releaseConversation(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  })

  const closeMutation = useMutation({
    mutationFn: ({ userId }: { userId: string }) => closeConversation(userId),
    onSuccess: () => {
      setSelectedUserId(null)
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
    onError: (err) => setSendError(err instanceof Error ? err.message : "Ошибка закрытия"),
  })

  const conversations = convList?.conversations ?? []
  const selected = conversations.find((c) => c.user_id === selectedUserId)

  return (
    <div className="grid gap-4 h-[calc(100vh-12rem)]" style={{ gridTemplateColumns: "350px 1fr" }}>
      {/* Conversation list */}
      <Card className="overflow-hidden flex flex-col">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Чаты</CardTitle>
            <select
              className="rounded border px-2 py-1 text-xs"
              value={filter}
              onChange={(e) => { setFilter(e.target.value); setSelectedUserId(null) }}
            >
              <option value="all">Все</option>
              <option value="attention">Позвали поддержку</option>
              <option value="taken_over">Перехваченные</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground p-4">Загрузка...</p>
          ) : conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4">Нет чатов</p>
          ) : (
            <div className="divide-y">
              {conversations.map((conv) => (
                <button
                  key={conv.user_id}
                  className={`w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors ${
                    conv.user_id === selectedUserId ? "bg-muted" : ""
                  }`}
                  onClick={() => setSelectedUserId(conv.user_id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm truncate">{conv.user_name}</span>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {conv.needs_attention && (
                        <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-[10px] rounded">Зовёт орга</span>
                      )}
                      {conv.taken_over && (
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded">Перехвачен</span>
                      )}
                      {conv.unread && <span className="w-2 h-2 bg-blue-500 rounded-full" />}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {conv.user_role || "пользователь"} - {conv.message_count} сообщ.
                  </p>
                  {conv.last_message && (
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">{conv.last_message}</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chat panel */}
      <Card className="overflow-hidden flex flex-col">
        {selected ? (
          <>
            <CardHeader className="pb-2 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">{selected.user_name}</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    @{selected.user_username || "N/A"} - {selected.user_role || "пользователь"}
                    {selected.taken_over && " (перехвачен)"}
                    {selected.status === "closed" && " (закрыт)"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {selected.taken_over && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => releaseMutation.mutate({ userId: selected.user_id })}
                      disabled={releaseMutation.isPending}
                    >
                      Вернуть бота
                    </Button>
                  )}
                  {selected.status === "open" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => closeMutation.mutate({ userId: selected.user_id })}
                      disabled={closeMutation.isPending}
                    >
                      Завершить диалог
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
              {messagesError && <p className="text-sm text-red-500">Не удалось загрузить сообщения</p>}
              {sendError && <p className="text-sm text-red-500">{sendError}</p>}
              {messages?.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "organizer" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === "organizer"
                        ? "bg-blue-500 text-white"
                        : msg.role === "assistant"
                          ? "bg-purple-500/15 border border-purple-500/30 text-foreground"
                          : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-xs opacity-70 mb-0.5">
                      {msg.role === "assistant" ? "AI-агент" : msg.role === "organizer" ? "Организатор" : selected.user_name}
                    </p>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <p className="text-[10px] opacity-50 mt-1">
                      {new Date(msg.created_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </CardContent>
            <div className="border-t p-3 flex gap-2">
              <input
                className="flex-1 rounded border px-3 py-2 text-sm"
                value={draftMessage}
                onChange={(e) => setDraftMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && draftMessage.trim()) {
                    e.preventDefault()
                    sendMutation.mutate({ userId: selected.user_id, text: draftMessage })
                  }
                }}
                placeholder="Написать как организатор..."
                disabled={sendMutation.isPending}
              />
              <Button
                onClick={() => sendMutation.mutate({ userId: selected.user_id, text: draftMessage })}
                disabled={!draftMessage.trim() || sendMutation.isPending}
              >
                Отправить
              </Button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <PageEmptyState
              icon={MessageCircle}
              title="Выберите чат"
              description="Выберите чат из списка слева для просмотра и ответа"
            />
          </div>
        )}
      </Card>
    </div>
  )
}
