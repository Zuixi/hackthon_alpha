import { useState, useRef, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Lightbulb, Plus, Trash2, Search, X, Upload, Flame,
  MessageSquare, Feather, Eye, Pen, Bold, Italic, Heading1,
  Heading2, List, ListOrdered, Quote, Code, Link, Sparkles,
  LayoutGrid, LayoutList,
} from 'lucide-react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from '@/components/ui/sheet'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { api } from '@/lib/api'
import type { HotTopic, IdeaCard } from '@/types/api'

const TAG_COLORS = [
  'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
  'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
  'bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-300',
  'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300',
] as const

const TAG_BAR_COLORS = [
  'bg-red-400', 'bg-amber-400', 'bg-blue-400', 'bg-green-400',
  'bg-indigo-400', 'bg-purple-400', 'bg-pink-400', 'bg-cyan-400',
] as const

const AI_TAG_KEYWORDS: Record<string, string[]> = {
  '渔民': ['社会热点', '人物故事', '渔业', '救援'],
  '救援': ['社会热点', '救援', '制度分析'],
  'AI': ['AI建议', '科技', '方法论'],
  '创作': ['方法论', '创作技巧', '个人成长'],
  '热点': ['社会热点', '流量分析', '创作技巧'],
  '安全': ['社会热点', '制度分析', '公共安全'],
  '科技': ['科技', 'AI建议', '前沿趋势'],
  '教育': ['教育', '社会热点', '方法论'],
}

function getTagColor(tag: string): string {
  let hash = 0
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

function getBarColor(tag: string): string {
  let hash = 0
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  return TAG_BAR_COLORS[Math.abs(hash) % TAG_BAR_COLORS.length]
}

function extractPlainText(markdown: string): string {
  return markdown
    .replace(/#{1,6}\s/g, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`{3}[\s\S]*?`{3}/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^[-*]\s/gm, '')
    .replace(/^\d+\.\s/gm, '')
    .replace(/^>\s/gm, '')
    .replace(/\n+/g, ' ')
    .trim()
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function getDisplayTitle(card: IdeaCard): string {
  if (card.title) return card.title
  const firstLine = card.content.split('\n').find(l => l.trim())
  if (!firstLine) return '无标题'
  return firstLine.replace(/^#{1,6}\s*/, '').replace(/\*\*/g, '').trim().slice(0, 60) || '无标题'
}

// --- Empty State ---

function EmptyState({ onCreate, hotTopic }: { onCreate: () => void; hotTopic?: HotTopic }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="cards-bulb-float w-20 h-20 bg-amber-50 dark:bg-amber-950/50 rounded-2xl flex items-center justify-center mb-6">
        <Lightbulb className="h-8 w-8 text-amber-400" />
      </div>

      <h3 className="text-xl font-semibold mb-2">
        每一个伟大的创作，都始于一个闪光的念头
      </h3>
      <p className="text-sm text-muted-foreground mb-8 max-w-md">
        灵感卡片是你创作旅程的素材库。随时记录、AI 辅助分析、一键关联热点，让好想法不再流失。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 max-w-2xl w-full">
        <ScenarioCard
          icon={<Flame className="h-5 w-5 text-orange-500" />}
          iconBg="bg-orange-100 dark:bg-orange-950"
          title="热点灵感"
          desc1="关联热搜话题"
          desc2="一键创建卡片"
          hoverBorder="hover:border-amber-300"
        />
        <ScenarioCard
          icon={<MessageSquare className="h-5 w-5 text-blue-500" />}
          iconBg="bg-blue-100 dark:bg-blue-950"
          title="对话摘录"
          desc1="AI 对话中"
          desc2="一键生成卡片"
          hoverBorder="hover:border-blue-300"
        />
        <ScenarioCard
          icon={<Feather className="h-5 w-5 text-green-500" />}
          iconBg="bg-green-100 dark:bg-green-950"
          title="随想笔记"
          desc1="随时记录想法"
          desc2="智能标签管理"
          hoverBorder="hover:border-green-300"
        />
      </div>

      <Button onClick={onCreate} className="px-8 py-3 rounded-xl text-sm font-medium shadow-lg mb-4">
        <Plus className="h-4 w-4 mr-1.5" />
        {hotTopic ? `记录关于「${hotTopic.title.slice(0, 15)}...」的灵感` : '创建我的第一张灵感卡片'}
      </Button>
      <p className="text-xs text-muted-foreground">
        或者从 <a href="/hot" className="text-primary hover:underline">热点广场</a> 中点击「记录灵感」快速开始
      </p>
    </div>
  )
}

function ScenarioCard({ icon, iconBg, title, desc1, desc2, hoverBorder }: {
  icon: React.ReactNode; iconBg: string; title: string
  desc1: string; desc2: string; hoverBorder: string
}) {
  return (
    <div className={`bg-card border rounded-2xl p-5 text-center ${hoverBorder} hover:shadow-lg transition-all cursor-default group`}>
      <div className={`w-12 h-12 ${iconBg} rounded-xl flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform`}>
        {icon}
      </div>
      <h4 className="font-medium mb-1">{title}</h4>
      <p className="text-xs text-muted-foreground">{desc1}<br />{desc2}</p>
    </div>
  )
}

// --- Create Panel ---

function CreatePanel({ open, onOpenChange, hotTopic, onCreated }: {
  open: boolean
  onOpenChange: (v: boolean) => void
  hotTopic?: HotTopic
  onCreated: () => void
}) {
  const queryClient = useQueryClient()
  const editorRef = useRef<HTMLTextAreaElement>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [aiTags, setAiTags] = useState<string[]>([])
  const [aiAnalyzing, setAiAnalyzing] = useState(false)
  const [isPreview, setIsPreview] = useState(false)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const aiTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (open) {
      setTitle(hotTopic ? hotTopic.title : '')
      setContent(hotTopic ? `## ${hotTopic.title}\n\n${hotTopic.excerpt || ''}` : '')
      setSelectedTags(hotTopic ? ['热点'] : [])
      setTagInput('')
      setAiTags([])
      setIsPreview(false)
      setSaveState('idle')
    }
  }, [open, hotTopic])

  const analyzeContent = useCallback((text: string) => {
    if (text.length < 5) {
      setAiTags([])
      return
    }
    const matched = new Set<string>()
    Object.entries(AI_TAG_KEYWORDS).forEach(([keyword, tags]) => {
      if (text.includes(keyword)) tags.forEach(t => matched.add(t))
    })
    if (matched.size === 0) ['创作笔记', '随想', '待整理'].forEach(t => matched.add(t))
    setAiTags(Array.from(matched).filter(t => !selectedTags.includes(t)).slice(0, 5))
  }, [selectedTags])

  const handleContentChange = useCallback((value: string) => {
    setContent(value)
    setAiAnalyzing(true)
    if (aiTimeoutRef.current) clearTimeout(aiTimeoutRef.current)
    aiTimeoutRef.current = setTimeout(() => {
      analyzeContent(value)
      setAiAnalyzing(false)
    }, 800)
  }, [analyzeContent])

  const addTag = useCallback((tag: string) => {
    if (!selectedTags.includes(tag)) {
      setSelectedTags(prev => [...prev, tag])
      setAiTags(prev => prev.filter(t => t !== tag))
    }
  }, [selectedTags])

  const removeTag = useCallback((tag: string) => {
    setSelectedTags(prev => prev.filter(t => t !== tag))
  }, [])

  const handleTagKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault()
      addTag(tagInput.trim())
      setTagInput('')
    }
  }, [tagInput, addTag])

  const insertMarkdown = useCallback((before: string, after: string) => {
    const editor = editorRef.current
    if (!editor) return
    const start = editor.selectionStart
    const end = editor.selectionEnd
    const text = editor.value
    const selected = text.substring(start, end)
    const newValue = text.substring(0, start) + before + selected + after + text.substring(end)
    setContent(newValue)
    requestAnimationFrame(() => {
      editor.focus()
      editor.setSelectionRange(start + before.length, start + before.length + selected.length)
    })
  }, [])

  const createMutation = useMutation({
    mutationFn: (data: { title?: string; content: string; tags: string[]; hot_topic_id?: string }) =>
      api.cards.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['card-tags'] })
      setSaveState('saved')
      setTimeout(() => {
        onOpenChange(false)
        onCreated()
      }, 600)
    },
  })

  const handleSave = () => {
    if (!content.trim()) return
    setSaveState('saving')
    createMutation.mutate({
      title: title.trim() || undefined,
      content,
      tags: selectedTags,
      hot_topic_id: hotTopic?.id,
    })
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        showCloseButton={false}
        className="w-[640px] max-w-[90vw] sm:max-w-[640px] flex flex-col gap-0 p-0"
      >
        <SheetHeader className="px-6 py-4 border-b flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-100 dark:bg-amber-950 rounded-lg flex items-center justify-center shrink-0">
              <Lightbulb className="h-4 w-4 text-amber-600" />
            </div>
            <div>
              <SheetTitle>捕捉新灵感</SheetTitle>
              <SheetDescription>AI 将自动分析并推荐标签</SheetDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsPreview(!isPreview)}>
              {isPreview ? <><Pen className="h-3.5 w-3.5 mr-1" />编辑</> : <><Eye className="h-3.5 w-3.5 mr-1" />预览</>}
            </Button>
            <SheetClose render={<Button variant="ghost" size="icon-sm" />}>
              <X className="h-4 w-4" />
            </SheetClose>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium mb-1.5">标题（可选）</label>
            <Input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="给你的灵感起个名字..."
              className="rounded-xl"
            />
          </div>

          {/* Markdown Toolbar */}
          {!isPreview && (
            <div className="flex items-center gap-0.5 bg-muted rounded-lg p-1.5 flex-wrap">
              <ToolbarBtn icon={<Bold className="h-3.5 w-3.5" />} title="粗体" onClick={() => insertMarkdown('**', '**')} />
              <ToolbarBtn icon={<Italic className="h-3.5 w-3.5" />} title="斜体" onClick={() => insertMarkdown('*', '*')} />
              <ToolbarBtn icon={<Heading1 className="h-3.5 w-3.5" />} title="标题" onClick={() => insertMarkdown('# ', '')} />
              <ToolbarBtn icon={<Heading2 className="h-3.5 w-3.5" />} title="副标题" onClick={() => insertMarkdown('## ', '')} />
              <div className="w-px h-5 bg-border mx-0.5" />
              <ToolbarBtn icon={<List className="h-3.5 w-3.5" />} title="列表" onClick={() => insertMarkdown('- ', '')} />
              <ToolbarBtn icon={<ListOrdered className="h-3.5 w-3.5" />} title="有序列表" onClick={() => insertMarkdown('1. ', '')} />
              <ToolbarBtn icon={<Quote className="h-3.5 w-3.5" />} title="引用" onClick={() => insertMarkdown('> ', '')} />
              <ToolbarBtn icon={<Code className="h-3.5 w-3.5" />} title="代码" onClick={() => insertMarkdown('```\n', '\n```')} />
              <ToolbarBtn icon={<Link className="h-3.5 w-3.5" />} title="链接" onClick={() => insertMarkdown('[', '](url)')} />
              <div className="flex-1" />
              <Button variant="ghost" size="sm" className="text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 text-xs h-7 px-2">
                <Sparkles className="h-3 w-3 mr-1" />AI 助手
              </Button>
            </div>
          )}

          {/* Editor / Preview */}
          {isPreview ? (
            <div className="w-full px-4 py-3 bg-card border rounded-xl min-h-[300px] prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{content || '*暂无内容*'}</ReactMarkdown>
            </div>
          ) : (
            <Textarea
              ref={editorRef}
              value={content}
              onChange={e => handleContentChange(e.target.value)}
              placeholder="记录你的灵感...（支持 Markdown）"
              rows={12}
              className="rounded-xl resize-none leading-relaxed font-serif"
            />
          )}

          {/* AI Recommended Tags */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
                智能标签
                <span className="text-xs text-muted-foreground font-normal">（点击添加）</span>
              </label>
              {aiAnalyzing && (
                <span className="text-xs text-indigo-500 animate-pulse">AI 正在分析内容...</span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap min-h-[36px]">
              {aiTags.length > 0 ? aiTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => addTag(tag)}
                  className="cards-ai-pulse px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 flex items-center gap-1.5 hover:shadow-md transition-all"
                >
                  <Plus className="h-2.5 w-2.5" />{tag}
                </button>
              )) : (
                <span className="text-sm text-muted-foreground italic">
                  {content.length > 4 ? '未匹配到推荐标签' : '输入内容后，AI 将自动推荐标签...'}
                </span>
              )}
            </div>
          </div>

          {/* Selected Tags */}
          <div>
            <label className="block text-sm font-medium mb-2">
              已选标签 <span className="text-muted-foreground font-normal">（回车添加自定义标签）</span>
            </label>
            <div
              className="flex items-center gap-2 flex-wrap p-3 bg-muted/50 border rounded-xl min-h-[44px] cursor-text"
              onClick={() => document.getElementById('cards-tag-input')?.focus()}
            >
              {selectedTags.map(tag => (
                <span key={tag} className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 ${getTagColor(tag)}`}>
                  {tag}
                  <button onClick={e => { e.stopPropagation(); removeTag(tag) }} className="hover:opacity-70">
                    <X className="h-2.5 w-2.5" />
                  </button>
                </span>
              ))}
              <input
                id="cards-tag-input"
                type="text"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder={selectedTags.length === 0 ? '输入标签...' : ''}
                className="bg-transparent text-sm outline-none min-w-[80px] flex-1 placeholder:text-muted-foreground"
              />
            </div>
          </div>

          {/* Linked Content */}
          <div>
            <label className="block text-sm font-medium mb-2">关联内容</label>
            <div className="grid grid-cols-2 gap-3">
              <div className="border rounded-xl p-3 bg-card">
                <div className="flex items-center gap-2 mb-1.5">
                  <Flame className="h-3.5 w-3.5 text-orange-500" />
                  <span className="text-xs font-medium">关联热点</span>
                </div>
                {hotTopic ? (
                  <>
                    <p className="text-sm text-muted-foreground truncate">{hotTopic.title}</p>
                    <div className="mt-2 flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                      <span>✓</span> 已自动关联
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">无关联热点</p>
                )}
              </div>
              <div className="border border-dashed rounded-xl p-3 bg-card">
                <div className="flex items-center gap-2 mb-1.5">
                  <MessageSquare className="h-3.5 w-3.5 text-blue-500" />
                  <span className="text-xs font-medium">关联对话</span>
                </div>
                <p className="text-sm text-muted-foreground">暂无关联</p>
              </div>
            </div>
          </div>
        </div>

        <SheetFooter className="px-6 py-4 border-t bg-muted/30 flex-row items-center justify-between">
          <span className="text-xs text-muted-foreground">支持 Markdown 格式</span>
          <div className="flex items-center gap-3">
            <SheetClose render={<Button variant="ghost" />}>取消</SheetClose>
            <Button
              onClick={handleSave}
              disabled={saveState !== 'idle' || !content.trim()}
              className={saveState === 'saved' ? 'bg-green-600 hover:bg-green-600' : ''}
            >
              {saveState === 'saving' ? '保存中...' : saveState === 'saved' ? '✓ 已保存' : '保存卡片'}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}

function ToolbarBtn({ icon, title, onClick }: { icon: React.ReactNode; title: string; onClick: () => void }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className="px-2 py-1.5 rounded text-muted-foreground hover:bg-background hover:text-foreground transition-all"
    >
      {icon}
    </button>
  )
}

// --- Card Detail Modal ---

function CardDetailModal({ card, open, onOpenChange, onDelete }: {
  card: IdeaCard | null
  open: boolean
  onOpenChange: (v: boolean) => void
  onDelete: (id: string) => void
}) {
  const navigate = useNavigate()

  if (!card) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col gap-0 p-0 rounded-2xl">
        <DialogHeader className="px-6 py-4 border-b flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${card.tags.length > 0 ? getBarColor(card.tags[0]) : 'bg-amber-400'}`} />
            <DialogTitle className="line-clamp-1">{getDisplayTitle(card)}</DialogTitle>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="prose prose-sm max-w-none dark:prose-invert font-serif leading-relaxed">
            <ReactMarkdown>{card.content}</ReactMarkdown>
          </div>
          <div className="mt-6 pt-4 border-t space-y-3">
            {card.tags.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-medium text-muted-foreground">标签：</span>
                {card.tags.map(tag => (
                  <span key={tag} className={`px-2.5 py-1 rounded-full text-xs font-medium ${getTagColor(tag)}`}>{tag}</span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>创建于 {relativeTime(card.created_at)}</span>
              <span>编辑于 {relativeTime(card.updated_at)}</span>
            </div>
          </div>
        </div>

        <DialogFooter className="px-6 py-4 border-t bg-muted/30 flex-row items-center justify-between sm:justify-between">
          <div className="flex items-center gap-2">
            {card.hot_topic_title && (
              <div className="border rounded-lg px-3 py-2 flex items-center gap-2 cursor-pointer hover:bg-muted/50 transition-colors">
                <Flame className="h-3 w-3 text-orange-500" />
                <span className="text-xs truncate max-w-[150px]">{card.hot_topic_title}</span>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={() => { onDelete(card.id); onOpenChange(false) }}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />删除
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                try {
                  await api.publish.toZhihu(card.content)
                  toast.success('已发布到知乎圈子')
                } catch {
                  toast.error('发布失败')
                }
              }}
            >
              <Upload className="h-3.5 w-3.5 mr-1" />发布
            </Button>
          </div>
          <Button
            size="sm"
            onClick={() => {
              navigate('/chat', { state: { cardContent: card.content } })
              onOpenChange(false)
            }}
          >
            <Pen className="h-3.5 w-3.5 mr-1" />基于这个灵感创作
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// --- Card Grid Item ---

function CardGridItem({ card, index, onClick }: { card: IdeaCard; index: number; onClick: () => void }) {
  const barColor = card.tags.length > 0 ? getBarColor(card.tags[0]) : 'bg-gray-300'

  return (
    <div
      onClick={onClick}
      className="cards-card-enter bg-card rounded-2xl border overflow-hidden cursor-pointer hover:-translate-y-1 hover:shadow-lg transition-all duration-300"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      <div className={`h-1 ${barColor}`} />
      <div className="p-5">
        <h3 className="font-semibold line-clamp-2 mb-2">{getDisplayTitle(card)}</h3>
        <p className="text-sm text-muted-foreground line-clamp-3 mb-4 leading-relaxed">
          {extractPlainText(card.content).slice(0, 120)}
        </p>

        {card.tags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap mb-3">
            {card.tags.map(tag => (
              <span key={tag} className={`px-2.5 py-1 rounded-full text-xs font-medium ${getTagColor(tag)}`}>{tag}</span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between pt-3 border-t">
          <div className="flex items-center gap-3">
            {card.hot_topic_title && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground" title={card.hot_topic_title}>
                <Flame className="h-3 w-3 text-orange-400" />
                <span className="truncate max-w-[80px]">{card.hot_topic_title}</span>
              </span>
            )}
            {card.chat_session_id && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <MessageSquare className="h-3 w-3 text-blue-400" />
                <span>对话</span>
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground">{relativeTime(card.updated_at)}</span>
        </div>
      </div>
    </div>
  )
}

function CardListItem({ card, onClick }: { card: IdeaCard; onClick: () => void }) {
  const barColor = card.tags.length > 0 ? getBarColor(card.tags[0]) : 'bg-gray-300'

  return (
    <div
      onClick={onClick}
      className="bg-card rounded-xl border overflow-hidden cursor-pointer hover:shadow-md transition-all flex"
    >
      <div className={`w-1 shrink-0 ${barColor}`} />
      <div className="flex-1 p-4 flex items-center gap-4 min-w-0">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{getDisplayTitle(card)}</h3>
          <p className="text-sm text-muted-foreground truncate mt-0.5">
            {extractPlainText(card.content).slice(0, 80)}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          {card.tags.slice(0, 2).map(tag => (
            <span key={tag} className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTagColor(tag)}`}>{tag}</span>
          ))}
          {card.tags.length > 2 && <span className="text-xs text-muted-foreground">+{card.tags.length - 2}</span>}
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">{relativeTime(card.updated_at)}</span>
      </div>
    </div>
  )
}

// --- Main Page ---

export function CardsPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const hotTopic = (location.state as { hotTopic?: HotTopic })?.hotTopic
  const [search, setSearch] = useState('')
  const [selectedTag, setSelectedTag] = useState('')
  const [createOpen, setCreateOpen] = useState(!!hotTopic)
  const [detailCard, setDetailCard] = useState<IdeaCard | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() =>
    (localStorage.getItem('cards-view') as 'grid' | 'list') || 'grid'
  )

  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards', { search, tag: selectedTag }],
    queryFn: () => api.cards.list({ search: search || undefined, tag: selectedTag || undefined }),
  })

  const { data: allTags } = useQuery({
    queryKey: ['card-tags'],
    queryFn: () => api.cards.tags(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.cards.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['card-tags'] })
      toast.success('卡片已删除')
    },
  })

  const handleViewChange = (mode: 'grid' | 'list') => {
    setViewMode(mode)
    localStorage.setItem('cards-view', mode)
  }

  const handleCreated = () => {
    const total = (cards?.total ?? 0) + 1
    toast.success(`灵感已捕捉！共 ${total} 张卡片`)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-100 dark:bg-amber-950 rounded-xl flex items-center justify-center">
            <Lightbulb className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold">灵感卡片</h2>
            <p className="text-sm text-muted-foreground">记录和管理你的创作灵感</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-muted rounded-lg p-1">
            <button
              onClick={() => handleViewChange('grid')}
              className={`px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'grid' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleViewChange('list')}
              className={`px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'list' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
            >
              <LayoutList className="h-4 w-4" />
            </button>
          </div>
          <Button onClick={() => setCreateOpen(true)} className="rounded-xl shadow-lg">
            <Plus className="h-4 w-4 mr-1.5" />
            捕捉灵感
          </Button>
        </div>
      </div>

      {/* Search + Tag Filter */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="搜索灵感标题、内容、标签..."
            className="pl-9 rounded-xl"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
        </div>
      </div>

      {allTags && allTags.length > 0 && (
        <div className="flex gap-2 mb-5 flex-wrap">
          <button
            onClick={() => setSelectedTag('')}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${selectedTag === '' ? 'bg-primary text-primary-foreground' : 'bg-card border text-muted-foreground hover:border-foreground/30'}`}
          >
            全部
          </button>
          {allTags.map(tag => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag === selectedTag ? '' : tag)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${selectedTag === tag ? getTagColor(tag) : 'bg-card border text-muted-foreground hover:border-foreground/30'}`}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="grid gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-card rounded-2xl border overflow-hidden">
              <Skeleton className="h-1 w-full" />
              <div className="p-5 space-y-3">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
                <div className="flex gap-2 pt-2">
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-16 rounded-full" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : cards && cards.items.length > 0 ? (
        viewMode === 'grid' ? (
          <div className="grid gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {cards.items.map((card, i) => (
              <CardGridItem key={card.id} card={card} index={i} onClick={() => setDetailCard(card)} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {cards.items.map(card => (
              <CardListItem key={card.id} card={card} onClick={() => setDetailCard(card)} />
            ))}
          </div>
        )
      ) : (
        <EmptyState onCreate={() => setCreateOpen(true)} hotTopic={hotTopic} />
      )}

      {/* Filtered empty */}
      {cards && cards.items.length === 0 && !isLoading && (search || selectedTag) && (
        <div className="text-center py-12 text-muted-foreground">
          <Search className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="mb-2">没有找到匹配的卡片</p>
          <Button variant="outline" size="sm" onClick={() => { setSearch(''); setSelectedTag('') }}>
            <X className="h-3.5 w-3.5 mr-1" />
            清除筛选
          </Button>
        </div>
      )}

      {/* Create Panel */}
      <CreatePanel
        open={createOpen}
        onOpenChange={setCreateOpen}
        hotTopic={hotTopic}
        onCreated={handleCreated}
      />

      {/* Detail Modal */}
      <CardDetailModal
        card={detailCard}
        open={!!detailCard}
        onOpenChange={v => { if (!v) setDetailCard(null) }}
        onDelete={id => deleteMutation.mutate(id)}
      />
    </div>
  )
}
