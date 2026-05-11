import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Send, Lightbulb, Copy, Upload } from 'lucide-react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { api } from '@/lib/api'
import { useAuth } from '@/hooks/use-auth'
import type { ChatMessage } from '@/types/api'

type StreamToolUse = {
  id: string
  name: string
  input: string
}

export function ChatSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingThinking, setStreamingThinking] = useState('')
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false)
  const [streamingToolUses, setStreamingToolUses] = useState<StreamToolUse[]>([])
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: session } = useQuery({
    queryKey: ['chat-session', sessionId],
    queryFn: () => api.chat.getSession(sessionId!),
    enabled: !!sessionId,
  })

  useEffect(() => {
    if (session?.messages) {
      setLocalMessages(session.messages)
    }
  }, [session?.messages])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(scrollToBottom, [localMessages, streamingContent, scrollToBottom])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isStreaming || !sessionId) return

    setInput('')
    setIsStreaming(true)
    setStreamingContent('')
    setStreamingThinking('')
    setIsThinkingExpanded(false)
    setStreamingToolUses([])

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }
    setLocalMessages((prev) => [...prev, userMsg])

    try {
      const res = await api.chat.sendMessage(sessionId, message)
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let accumulatedThinking = ''
      let buffer = ''
      const toolMap = new Map<string, StreamToolUse>()

      const parseEvent = (rawEvent: string) => {
        const lines = rawEvent.split('\n')
        const dataLines = lines
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
        if (dataLines.length === 0) return
        const data = dataLines.join('\n')
        if (data === '[DONE]') return

        try {
          const parsed = JSON.parse(data)
          const type = parsed.type as string | undefined

          // Backward compatibility with old backend payload shape.
          if (!type && parsed.content) {
            accumulated += parsed.content
            setStreamingContent(accumulated)
            return
          }

          if (type === 'text_delta' && parsed.content) {
            accumulated += parsed.content
            setStreamingContent(accumulated)
            return
          }

          if (type === 'thinking_delta' && parsed.content) {
            accumulatedThinking += parsed.content
            setStreamingThinking(accumulatedThinking)
            return
          }

          if (type === 'tool_use_start') {
            const id = parsed.id || `tool-${Date.now()}`
            const item: StreamToolUse = { id, name: parsed.name || 'tool', input: '' }
            toolMap.set(id, item)
            setStreamingToolUses(Array.from(toolMap.values()))
            return
          }

          if (type === 'tool_use_delta' && parsed.id) {
            const existing = toolMap.get(parsed.id)
            if (existing && parsed.content) {
              existing.input += String(parsed.content)
              toolMap.set(parsed.id, existing)
              setStreamingToolUses(Array.from(toolMap.values()))
            }
            return
          }

          if (type === 'tool_use') {
            const id = parsed.id || `tool-${Date.now()}`
            const existing = toolMap.get(id) || {
              id,
              name: parsed.name || 'tool',
              input: '',
            }
            existing.name = parsed.name || existing.name
            if (parsed.input !== undefined) {
              existing.input =
                typeof parsed.input === 'string'
                  ? parsed.input
                  : JSON.stringify(parsed.input, null, 2)
            }
            toolMap.set(id, existing)
            setStreamingToolUses(Array.from(toolMap.values()))
            return
          }

          if (type === 'error') {
            toast.error(parsed.message || '流式响应异常')
          }
        } catch {
          // skip malformed chunks
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        let delimiterIndex = buffer.indexOf('\n\n')

        while (delimiterIndex !== -1) {
          const rawEvent = buffer.slice(0, delimiterIndex)
          buffer = buffer.slice(delimiterIndex + 2)
          parseEvent(rawEvent)
          delimiterIndex = buffer.indexOf('\n\n')
        }
      }

      if (buffer.trim()) {
        parseEvent(buffer)
      }

      if (accumulated) {
        const assistantMsg: ChatMessage = {
          id: `temp-assistant-${Date.now()}`,
          role: 'assistant',
          content: accumulated,
          created_at: new Date().toISOString(),
        }
        setLocalMessages((prev) => [...prev, assistantMsg])
      }
    } catch (err) {
      console.error('Streaming failed:', err)
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
      setStreamingThinking('')
      setStreamingToolUses([])
      queryClient.invalidateQueries({ queryKey: ['chat-session', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSaveCard = async (content: string) => {
    try {
      await api.cards.create({
        content,
        tags: ['AI创作'],
        hot_topic_id: session?.hot_topic_id ?? undefined,
        chat_session_id: sessionId,
      })
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      toast.success('已保存为灵感卡片')
    } catch {
      toast.error('保存失败')
    }
  }

  const handlePublish = async (content: string) => {
    try {
      const result = await api.publish.toZhihu(content)
      if (result.success) {
        toast.success('已发布到知乎圈子')
      }
    } catch {
      toast.error('发布失败，请确保已登录知乎')
    }
  }

  const allMessages = localMessages

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-3 border-b bg-background">
        <Button variant="ghost" size="icon" onClick={() => navigate('/chat')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h3 className="font-medium truncate">{session?.title || '对话'}</h3>
          {session?.hot_topic_title && (
            <p className="text-xs text-muted-foreground truncate">
              热点: {session.hot_topic_title}
            </p>
          )}
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-6">
          {allMessages.length === 0 && !isStreaming && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg mb-2">开始创作对话</p>
              <p className="text-sm">输入你的想法，AI 助手会帮你分析热点、提供切入角度</p>
            </div>
          )}

          {allMessages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              userName={user?.name || '我'}
              onSaveCard={handleSaveCard}
              onPublish={handlePublish}
            />
          ))}

          {isStreaming && (streamingThinking || streamingToolUses.length > 0 || streamingContent) && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">AI</AvatarFallback>
              </Avatar>
              <div className="flex-1 bg-muted rounded-2xl rounded-tl-none px-4 py-3">
                {!!streamingThinking && (
                  <div className="mb-3 rounded-md border bg-background/70 px-3 py-2">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="text-[11px] font-medium text-muted-foreground">Thinking</p>
                      <button
                        type="button"
                        className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => setIsThinkingExpanded((prev) => !prev)}
                      >
                        {isThinkingExpanded ? '收起' : '展开'}
                      </button>
                    </div>
                    {isThinkingExpanded ? (
                      <p className="text-xs whitespace-pre-wrap text-muted-foreground">{streamingThinking}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground">思考过程已折叠，点击“展开”查看。</p>
                    )}
                  </div>
                )}
                {streamingToolUses.length > 0 && (
                  <div className="mb-3 space-y-2">
                    {streamingToolUses.map((tool) => (
                      <div key={tool.id} className="rounded-md border bg-background/70 px-3 py-2">
                        <p className="text-[11px] font-medium text-muted-foreground">
                          Tool: {tool.name}
                        </p>
                        {tool.input && (
                          <pre className="mt-1 text-xs whitespace-pre-wrap break-words text-muted-foreground">
                            {tool.input}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown>{streamingContent}</ReactMarkdown>
                </div>
                <div className="mt-1">
                  <span className="inline-block w-2 h-4 bg-primary animate-pulse rounded-sm" />
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-4 bg-background">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的想法... (Enter 发送, Shift+Enter 换行)"
            className="min-h-[44px] max-h-[120px] resize-none"
            rows={1}
            disabled={isStreaming}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-11 w-11 flex-shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({
  message,
  userName,
  onSaveCard,
  onPublish,
}: {
  message: ChatMessage
  userName: string
  onSaveCard: (content: string) => void
  onPublish: (content: string) => void
}) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar className="h-8 w-8 flex-shrink-0">
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground text-xs' : 'bg-primary/10 text-primary text-xs'}>
          {isUser ? userName[0] : 'AI'}
        </AvatarFallback>
      </Avatar>
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block text-left px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-none'
              : 'bg-muted rounded-tl-none'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && (
          <div className="flex gap-1 mt-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => onSaveCard(message.content)}
            >
              <Lightbulb className="h-3 w-3 mr-1" />
              保存灵感
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => onPublish(message.content)}
            >
              <Upload className="h-3 w-3 mr-1" />
              发布知乎
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => { navigator.clipboard.writeText(message.content); toast.success('已复制') }}
            >
              <Copy className="h-3 w-3 mr-1" />
              复制
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
