import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { Lightbulb, Plus, Trash2, Tag, Search, X, Upload } from 'lucide-react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import type { HotTopic } from '@/types/api'

export function CardsPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const hotTopic = (location.state as { hotTopic?: HotTopic })?.hotTopic
  const [search, setSearch] = useState('')
  const [selectedTag, setSelectedTag] = useState<string>('')
  const [createOpen, setCreateOpen] = useState(!!hotTopic)
  const [newContent, setNewContent] = useState(
    hotTopic ? `## ${hotTopic.title}\n\n${hotTopic.excerpt || ''}` : ''
  )
  const [newTags, setNewTags] = useState(hotTopic ? '热点' : '')

  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards', { search, tag: selectedTag }],
    queryFn: () => api.cards.list({ search: search || undefined, tag: selectedTag || undefined }),
  })

  const { data: allTags } = useQuery({
    queryKey: ['card-tags'],
    queryFn: () => api.cards.tags(),
  })

  const createMutation = useMutation({
    mutationFn: (data: { content: string; tags: string[]; hot_topic_id?: string }) =>
      api.cards.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['card-tags'] })
      setCreateOpen(false)
      setNewContent('')
      setNewTags('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.cards.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['card-tags'] })
    },
  })

  const handleCreate = () => {
    if (!newContent.trim()) return
    const tags = newTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    createMutation.mutate({
      content: newContent,
      tags,
      hot_topic_id: hotTopic?.id,
    })
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500" />
            灵感卡片
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            记录和管理你的创作灵感
          </p>
        </div>

        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger>
            <Button>
              <Plus className="h-4 w-4 mr-1" />
              新建卡片
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>新建灵感卡片</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-2">
              <Textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="记录你的灵感... (支持 Markdown)"
                rows={8}
              />
              <div>
                <label className="text-sm font-medium mb-1 block">
                  <Tag className="h-3.5 w-3.5 inline mr-1" />
                  标签（逗号分隔）
                </label>
                <Input
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="例如: 科技, 热点, 写作技巧"
                />
              </div>
              <Button className="w-full" onClick={handleCreate} disabled={createMutation.isPending}>
                {createMutation.isPending ? '保存中...' : '保存卡片'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索灵感..."
            className="pl-9"
          />
        </div>
      </div>

      {allTags && allTags.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <Badge
            variant={selectedTag === '' ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setSelectedTag('')}
          >
            全部
          </Badge>
          {allTags.map((tag) => (
            <Badge
              key={tag}
              variant={selectedTag === tag ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setSelectedTag(tag === selectedTag ? '' : tag)}
            >
              {tag}
            </Badge>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-full mb-1" />
                  <Skeleton className="h-4 w-1/2" />
                </CardContent>
              </Card>
            ))
          : cards?.items.map((card) => (
              <Card key={card.id} className="group hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="prose prose-sm max-w-none dark:prose-invert line-clamp-6 mb-3">
                    <ReactMarkdown>{card.content}</ReactMarkdown>
                  </div>

                  {card.tags.length > 0 && (
                    <div className="flex gap-1 flex-wrap mb-2">
                      {card.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{new Date(card.created_at).toLocaleDateString('zh-CN')}</span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={async () => {
                          try {
                            await api.publish.toZhihu(card.content)
                            toast.success('已发布到知乎圈子')
                          } catch {
                            toast.error('发布失败')
                          }
                        }}
                      >
                        <Upload className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => deleteMutation.mutate(card.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {card.hot_topic_title && (
                    <p className="text-xs text-muted-foreground mt-1 truncate">
                      热点: {card.hot_topic_title}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
      </div>

      {cards && cards.items.length === 0 && !isLoading && (
        <div className="text-center py-12 text-muted-foreground">
          <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="mb-2">
            {search || selectedTag ? '没有找到匹配的卡片' : '还没有灵感卡片'}
          </p>
          {(search || selectedTag) && (
            <Button variant="outline" size="sm" onClick={() => { setSearch(''); setSelectedTag('') }}>
              <X className="h-3.5 w-3.5 mr-1" />
              清除筛选
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
