import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Send, Lightbulb, Copy, Upload, ChevronDown, ChevronRight, Brain } from 'lucide-react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { api } from '@/lib/api'
import { useAuth } from '@/hooks/use-auth'
import type { ChatMessage } from '@/types/api'

type ProcessEntry =
  | { kind: 'thinking'; content: string }
  | { kind: 'tool_call'; name: string; input: string }
  | { kind: 'tool_result'; name: string; preview: string }
  | { kind: 'intermediate_text'; content: string }

const remarkPlugins = [remarkGfm]

export function ChatSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [displayedContent, setDisplayedContent] = useState('')
  const [streamingThinking, setStreamingThinking] = useState('')
  const [processLog, setProcessLog] = useState<ProcessEntry[]>([])
  const [isProcessExpanded, setIsProcessExpanded] = useState(false)
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const typewriterRef = useRef<number | null>(null)
  const displayedLenRef = useRef(0)
  const userScrolledAwayRef = useRef(false)
  const bottomSentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isStreaming) {
      if (typewriterRef.current) cancelAnimationFrame(typewriterRef.current)
      displayedLenRef.current = 0
      setDisplayedContent('')
      return
    }

    const tick = () => {
      const target = streamingContent
      const current = displayedLenRef.current
      if (current < target.length) {
        const gap = target.length - current
        const step = gap > 60 ? Math.ceil(gap / 8) : gap > 20 ? 3 : 1
        displayedLenRef.current = Math.min(current + step, target.length)
        setDisplayedContent(target.slice(0, displayedLenRef.current))
      }
      typewriterRef.current = requestAnimationFrame(tick)
    }

    typewriterRef.current = requestAnimationFrame(tick)
    return () => {
      if (typewriterRef.current) cancelAnimationFrame(typewriterRef.current)
    }
  }, [isStreaming, streamingContent])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    userScrolledAwayRef.current = distanceFromBottom > 80
  }, [])

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
    if (userScrolledAwayRef.current) return
    bottomSentinelRef.current?.scrollIntoView({ behavior: 'instant' })
  }, [])

  useEffect(scrollToBottom, [localMessages, displayedContent, scrollToBottom])

  useEffect(() => {
    userScrolledAwayRef.current = false
  }, [localMessages.length])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isStreaming || !sessionId) return

    setInput('')
    setIsStreaming(true)
    setStreamingContent('')
    setStreamingThinking('')
    setProcessLog([])
    setIsProcessExpanded(false)

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
      let accThinking = ''
      let buffer = ''
      const log: ProcessEntry[] = []
      let hasToolCalls = false

      const flushTextToProcess = () => {
        if (accumulated.trim()) {
          log.push({ kind: 'intermediate_text', content: accumulated.trim() })
          setProcessLog([...log])
        }
        accumulated = ''
        setStreamingContent('')
        displayedLenRef.current = 0
      }

      const flushThinkingToProcess = () => {
        if (accThinking.trim()) {
          log.push({ kind: 'thinking', content: accThinking.trim() })
          setProcessLog([...log])
        }
        accThinking = ''
        setStreamingThinking('')
      }

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
            accThinking += parsed.content
            setStreamingThinking(accThinking)
            return
          }

          if (type === 'tool_use_start' || type === 'tool_call' || type === 'tool_use') {
            flushThinkingToProcess()
            flushTextToProcess()
            hasToolCalls = true

            const name = parsed.name || 'tool'
            let inp = ''
            if (parsed.input !== undefined) {
              inp = typeof parsed.input === 'string'
                ? parsed.input
                : JSON.stringify(parsed.input, null, 2)
            }
            log.push({ kind: 'tool_call', name, input: inp })
            setProcessLog([...log])
            return
          }

          if (type === 'tool_use_delta' || type === 'tool_use_end') {
            return
          }

          if (type === 'tool_result') {
            const name = parsed.name || ''
            const preview = parsed.result_preview || ''
            log.push({ kind: 'tool_result', name, preview })
            setProcessLog([...log])
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

      flushThinkingToProcess()

      if (accumulated) {
        const assistantMsg: ChatMessage = {
          id: `temp-assistant-${Date.now()}`,
          role: 'assistant',
          content: accumulated,
          created_at: new Date().toISOString(),
        }
        setLocalMessages((prev) => [...prev, assistantMsg])
      } else if (hasToolCalls) {
        const lastTexts = log.filter(e => e.kind === 'intermediate_text')
        const fallbackContent = lastTexts.length > 0
          ? (lastTexts[lastTexts.length - 1] as { content: string }).content
          : '[AI 已完成处理]'
        const assistantMsg: ChatMessage = {
          id: `temp-assistant-${Date.now()}`,
          role: 'assistant',
          content: fallbackContent,
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
      setProcessLog([])
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

  const hasProcess = processLog.length > 0 || !!streamingThinking
  const toolCallCount = processLog.filter(e => e.kind === 'tool_call').length

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-3 border-b bg-background flex-shrink-0">
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

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto p-4"
      >
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

          {isStreaming && (hasProcess || displayedContent) && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">AI</AvatarFallback>
              </Avatar>
              <div className="flex-1 bg-muted rounded-2xl rounded-tl-none px-4 py-3">
                {hasProcess && (
                  <div className="mb-3 rounded-md border bg-background/70 overflow-hidden">
                    <button
                      type="button"
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/50 transition-colors"
                      onClick={() => setIsProcessExpanded((prev) => !prev)}
                    >
                      {isProcessExpanded
                        ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                        : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                      }
                      <Brain className="h-3.5 w-3.5 text-primary/70" />
                      <span className="text-[11px] font-medium text-muted-foreground">
                        思考过程
                        {toolCallCount > 0 ? (
                          <span className="ml-1.5 text-primary/60">
                            · 已调用 {toolCallCount} 个工具
                          </span>
                        ) : streamingThinking ? (
                          <span className="ml-1.5 text-primary/60 animate-pulse">
                            · 思考中...
                          </span>
                        ) : null}
                      </span>
                    </button>
                    {isProcessExpanded && (
                      <div className="border-t px-3 py-2 space-y-2 max-h-[300px] overflow-y-auto">
                        {processLog.map((entry, i) => (
                          <ProcessEntryView key={i} entry={entry} />
                        ))}
                        {streamingThinking && (
                          <p className="text-xs whitespace-pre-wrap text-muted-foreground leading-relaxed">
                            {streamingThinking}
                            <span className="inline-block w-1.5 h-3 bg-primary/50 animate-pulse rounded-sm ml-0.5 align-middle" />
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {displayedContent && (
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={remarkPlugins}>{displayedContent}</ReactMarkdown>
                  </div>
                )}
                <div className="mt-1">
                  <span className="inline-block w-2 h-4 bg-primary animate-pulse rounded-sm" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomSentinelRef} className="h-1" />
        </div>
      </div>

      <div className="flex-shrink-0 border-t p-4 bg-background">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={'输入你的想法... (Enter 发送, Shift+Enter 换行)'}
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

function ProcessEntryView({ entry }: { entry: ProcessEntry }) {
  if (entry.kind === 'thinking') {
    return (
      <p className="text-xs whitespace-pre-wrap text-muted-foreground leading-relaxed">
        {entry.content}
      </p>
    )
  }
  if (entry.kind === 'tool_call') {
    return (
      <div className="flex items-start gap-1.5">
        <span className="text-[11px] font-mono text-primary/70 whitespace-nowrap mt-0.5">
          {'▶'} {entry.name}
        </span>
        {entry.input && (
          <pre className="text-[10px] text-muted-foreground/70 truncate flex-1">{entry.input}</pre>
        )}
      </div>
    )
  }
  if (entry.kind === 'tool_result') {
    return (
      <div className="flex items-start gap-1.5">
        <span className="text-[11px] font-mono text-green-600/70 whitespace-nowrap mt-0.5">
          {'✓'} {entry.name}
        </span>
        {entry.preview && (
          <pre className="text-[10px] text-muted-foreground/60 truncate flex-1">
            {entry.preview.length > 100 ? entry.preview.slice(0, 100) + '...' : entry.preview}
          </pre>
        )}
      </div>
    )
  }
  if (entry.kind === 'intermediate_text') {
    return (
      <p className="text-xs text-muted-foreground/80 italic border-l-2 border-primary/20 pl-2">
        {entry.content}
      </p>
    )
  }
  return null
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
              <ReactMarkdown remarkPlugins={remarkPlugins}>{message.content}</ReactMarkdown>
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
              {'保存灵感'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => onPublish(message.content)}
            >
              <Upload className="h-3 w-3 mr-1" />
              {'发布知乎'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => { navigator.clipboard.writeText(message.content); toast.success('已复制') }}
            >
              <Copy className="h-3 w-3 mr-1" />
              {'复制'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
