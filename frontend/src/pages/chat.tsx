import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Plus, Trash2, Clock, Pencil, Check, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'

export function ChatPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => api.chat.listSessions(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.chat.deleteSession(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-sessions'] }),
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      api.chat.renameSession(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setEditingId(null)
      toast.success('已重命名')
    },
    onError: () => toast.error('重命名失败'),
  })

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editingId])

  const handleNewChat = async () => {
    try {
      const session = await api.chat.createSession()
      navigate(`/chat/${session.id}`)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const startEditing = (id: string, currentTitle: string) => {
    setEditingId(id)
    setEditTitle(currentTitle)
  }

  const confirmRename = () => {
    if (!editingId) return
    const trimmed = editTitle.trim()
    if (!trimmed) {
      setEditingId(null)
      return
    }
    renameMutation.mutate({ id: editingId, title: trimmed })
  }

  const cancelEditing = () => {
    setEditingId(null)
    setEditTitle('')
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      confirmRename()
    } else if (e.key === 'Escape') {
      cancelEditing()
    }
  }

  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
    if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
    return d.toLocaleDateString('zh-CN')
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <MessageSquare className="h-6 w-6 text-blue-500" />
            创作对话
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            与 AI 助手一起头脑风暴，创作优质内容
          </p>
        </div>
        <Button onClick={handleNewChat}>
          <Plus className="h-4 w-4 mr-1" />
          新对话
        </Button>
      </div>

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-5 w-1/2 mb-2" />
                  <Skeleton className="h-4 w-1/4" />
                </CardContent>
              </Card>
            ))
          : sessions?.map((session) => (
              <Card
                key={session.id}
                className="group cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => {
                  if (editingId !== session.id) navigate(`/chat/${session.id}`)
                }}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      {editingId === session.id ? (
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <Input
                            ref={inputRef}
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={handleEditKeyDown}
                            onBlur={confirmRename}
                            className="h-8 text-sm font-medium"
                            placeholder="输入对话名称"
                            disabled={renameMutation.isPending}
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 flex-shrink-0"
                            onMouseDown={(e) => { e.preventDefault(); confirmRename() }}
                          >
                            <Check className="h-3.5 w-3.5 text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 flex-shrink-0"
                            onMouseDown={(e) => { e.preventDefault(); cancelEditing() }}
                          >
                            <X className="h-3.5 w-3.5 text-muted-foreground" />
                          </Button>
                        </div>
                      ) : (
                        <h3 className="font-medium truncate">{session.title}</h3>
                      )}
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTime(session.updated_at)}
                        </span>
                        <span>{session.message_count} 条消息</span>
                        {session.hot_topic_title && (
                          <span className="truncate max-w-[200px]">
                            关联热点: {session.hot_topic_title}
                          </span>
                        )}
                      </div>
                    </div>
                    {editingId !== session.id && (
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation()
                            startEditing(session.id, session.title)
                          }}
                        >
                          <Pencil className="h-4 w-4 text-muted-foreground" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteMutation.mutate(session.id)
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {sessions && sessions.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="mb-4">还没有对话</p>
          <Button onClick={handleNewChat}>
            <Plus className="h-4 w-4 mr-1" />
            开始第一次创作对话
          </Button>
        </div>
      )}
    </div>
  )
}
