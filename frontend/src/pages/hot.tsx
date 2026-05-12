import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Flame,
  ExternalLink,
  MessageSquare,
  Lightbulb,
  RefreshCw,
  ArrowUpDown,
  Clock,
  TrendingUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import type { HotTopic } from '@/types/api'

type SortMode = 'hot' | 'time'

const TOP3_COLORS = [
  'bg-red-500 text-white',
  'bg-orange-500 text-white',
  'bg-amber-500 text-white',
]

export function HotPage() {
  const navigate = useNavigate()
  const [sortMode, setSortMode] = useState<SortMode>('hot')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['hot-topics'],
    queryFn: () => api.hot.list(50),
    staleTime: 60_000,
  })

  const sortedItems = useMemo(() => {
    if (!data?.items) return []
    const items = [...data.items]
    if (sortMode === 'time') {
      return items.sort(
        (a, b) => new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime(),
      )
    }
    return items.sort((a, b) => b.hot_score - a.hot_score)
  }, [data?.items, sortMode])

  const handleStartChat = async (topic: HotTopic) => {
    try {
      const session = await api.chat.createSession(topic.id)
      navigate(`/chat/${session.id}`)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Flame className="h-6 w-6 text-orange-500" />
            热点广场
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            知乎实时热榜，发现创作灵感
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border bg-muted p-0.5">
            <Button
              variant={sortMode === 'hot' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={() => setSortMode('hot')}
            >
              <TrendingUp className="h-3 w-3" />
              热度
            </Button>
            <Button
              variant={sortMode === 'time' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={() => setSortMode('time')}
            >
              <Clock className="h-3 w-3" />
              时间
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      {data && data.items.length > 0 && (
        <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <ArrowUpDown className="h-3.5 w-3.5" />
            共 {data.total} 条热点
          </span>
          <Badge variant="outline" className="text-xs font-normal">
            知乎热榜
          </Badge>
        </div>
      )}

      {/* Topic list */}
      <div className="space-y-2">
        {isLoading
          ? Array.from({ length: 10 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
                    <div className="flex-1">
                      <Skeleton className="h-5 w-3/4 mb-2" />
                      <Skeleton className="h-4 w-full mb-1" />
                      <Skeleton className="h-3 w-1/3" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          : sortedItems.map((topic, index) => (
              <Card key={topic.id} className="group hover:shadow-md transition-all duration-200">
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <span
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        index < 3
                          ? TOP3_COLORS[index]
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-foreground leading-snug mb-1">
                        {topic.title}
                      </h3>
                      {topic.excerpt && (
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                          {topic.excerpt}
                        </p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        {topic.hot_score > 0 && (
                          <Badge variant="secondary" className="text-xs">
                            <Flame className="h-3 w-3 mr-1 text-orange-500" />
                            {topic.hot_score.toLocaleString()}
                          </Badge>
                        )}
                        {topic.answer_count > 0 && <span>{topic.answer_count} 回答</span>}
                        {topic.follower_count > 0 && <span>{topic.follower_count} 关注</span>}
                      </div>
                    </div>
                    <div className="flex-shrink-0 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button size="sm" variant="default" onClick={() => handleStartChat(topic)}>
                        <MessageSquare className="h-3.5 w-3.5 mr-1" />
                        创作
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate('/cards', { state: { hotTopic: topic } })}
                      >
                        <Lightbulb className="h-3.5 w-3.5 mr-1" />
                        灵感
                      </Button>
                      {topic.url && (
                        <a
                          href={topic.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:bg-muted transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Empty state */}
      {data && data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Flame className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>暂无热点数据</p>
          <Separator className="my-4 max-w-xs mx-auto" />
          <Button variant="outline" onClick={() => refetch()}>
            刷新试试
          </Button>
        </div>
      )}
    </div>
  )
}
