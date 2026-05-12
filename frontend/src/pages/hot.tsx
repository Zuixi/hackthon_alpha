import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Flame,
  ExternalLink,
  MessageSquare,
  Lightbulb,
  RefreshCw,
  Clock,
  TrendingUp,
  Calendar,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import type { HotTopic, HotDayGroup } from '@/types/api'

type ViewMode = 'latest' | 'history'

const TOP3_COLORS = [
  'bg-red-500 text-white',
  'bg-orange-500 text-white',
  'bg-amber-500 text-white',
]

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = today.getTime() - date.getTime()
  const dayDiff = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (dayDiff === 0) return '今天'
  if (dayDiff === 1) return '昨天'
  if (dayDiff === 2) return '前天'

  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${dateStr.slice(5)} ${weekdays[date.getDay()]}`
}

function formatBatchTime(batchStr: string): string {
  if (!batchStr) return ''
  const parts = batchStr.split('T')
  if (parts.length < 2) return batchStr
  return parts[1].slice(0, 5)
}

function TopicItem({
  topic,
  index,
  onStartChat,
  onInspiration,
}: {
  topic: HotTopic
  index: number
  onStartChat: (topic: HotTopic) => void
  onInspiration: (topic: HotTopic) => void
}) {
  return (
    <div className="group flex items-start gap-3 py-3 px-2 rounded-lg hover:bg-muted/50 transition-colors">
      <span
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
          index < 3 ? TOP3_COLORS[index] : 'bg-muted text-muted-foreground'
        }`}
      >
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-foreground leading-snug">
          {topic.title}
        </h4>
        {topic.excerpt && (
          <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
            {topic.excerpt}
          </p>
        )}
      </div>
      <div className="flex-shrink-0 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button size="sm" variant="default" className="h-7 text-xs" onClick={() => onStartChat(topic)}>
          <MessageSquare className="h-3 w-3 mr-1" />
          创作
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => onInspiration(topic)}>
          <Lightbulb className="h-3 w-3 mr-1" />
          灵感
        </Button>
        {topic.url && (
          <a
            href={topic.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-7 w-7 rounded-md text-muted-foreground hover:bg-muted transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  )
}

function DayCard({
  dayGroup,
  onStartChat,
  onInspiration,
}: {
  dayGroup: HotDayGroup
  onStartChat: (topic: HotTopic) => void
  onInspiration: (topic: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const latestBatch = dayGroup.batches[0]
  if (!latestBatch) return null

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="h-4 w-4 text-blue-500" />
            {formatDate(dayGroup.date)}
            <Badge variant="secondary" className="text-xs font-normal">
              {dayGroup.topic_count} 条热点
            </Badge>
            <Badge variant="outline" className="text-xs font-normal">
              {dayGroup.batches.length} 次更新
            </Badge>
          </CardTitle>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2">
          {dayGroup.batches.map((batch) => (
            <div key={batch.fetch_batch} className="mb-3 last:mb-0">
              <div className="flex items-center gap-2 mb-1 px-2">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium">
                  {formatBatchTime(batch.fetch_batch)} 更新 · {batch.count} 条
                </span>
              </div>
              <div className="divide-y divide-border/50">
                {batch.items.map((topic, idx) => (
                  <TopicItem
                    key={topic.id}
                    topic={topic}
                    index={idx}
                    onStartChat={onStartChat}
                    onInspiration={onInspiration}
                  />
                ))}
              </div>
              {batch !== dayGroup.batches[dayGroup.batches.length - 1] && (
                <Separator className="my-2" />
              )}
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  )
}

export function HotPage() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>('latest')

  const latestQuery = useQuery({
    queryKey: ['hot-topics'],
    queryFn: () => api.hot.list(30),
    staleTime: 60_000,
    enabled: viewMode === 'latest',
  })

  const historyQuery = useQuery({
    queryKey: ['hot-history'],
    queryFn: () => api.hot.history(5),
    staleTime: 120_000,
    enabled: viewMode === 'history',
  })

  const isLoading = viewMode === 'latest' ? latestQuery.isLoading : historyQuery.isLoading
  const isFetching = viewMode === 'latest' ? latestQuery.isFetching : historyQuery.isFetching

  const handleRefresh = () => {
    if (viewMode === 'latest') latestQuery.refetch()
    else historyQuery.refetch()
  }

  const handleStartChat = async (topic: HotTopic) => {
    try {
      const session = await api.chat.createSession(topic.id)
      navigate(`/chat/${session.id}`)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const handleInspiration = (topic: HotTopic) => {
    navigate('/cards', { state: { hotTopic: topic } })
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
            知乎实时热榜，发现创作灵感 · 每30分钟自动更新
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border bg-muted p-0.5">
            <Button
              variant={viewMode === 'latest' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={() => setViewMode('latest')}
            >
              <TrendingUp className="h-3 w-3" />
              最新
            </Button>
            <Button
              variant={viewMode === 'history' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={() => setViewMode('history')}
            >
              <Calendar className="h-3 w-3" />
              历史
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="space-y-3">
                  <Skeleton className="h-5 w-1/3" />
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="flex items-start gap-3">
                      <Skeleton className="h-7 w-7 rounded-full flex-shrink-0" />
                      <div className="flex-1">
                        <Skeleton className="h-4 w-3/4 mb-1" />
                        <Skeleton className="h-3 w-full" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Latest view */}
      {!isLoading && viewMode === 'latest' && (
        <>
          {latestQuery.data && latestQuery.data.items.length > 0 && (
            <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
              <span>共 {latestQuery.data.total} 条热点</span>
              <Badge variant="outline" className="text-xs font-normal">
                知乎热榜
              </Badge>
            </div>
          )}
          <div className="space-y-1">
            {latestQuery.data?.items.map((topic, index) => (
              <Card key={topic.id} className="group hover:shadow-md transition-all duration-200">
                <CardContent className="p-3">
                  <TopicItem
                    topic={topic}
                    index={index}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
          {latestQuery.data && latestQuery.data.items.length === 0 && (
            <EmptyState onRefresh={handleRefresh} />
          )}
        </>
      )}

      {/* History view */}
      {!isLoading && viewMode === 'history' && (
        <>
          {historyQuery.data && historyQuery.data.days.length > 0 && (
            <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
              <span>最近 {historyQuery.data.total_days} 天的热榜记录</span>
            </div>
          )}
          <div className="space-y-4">
            {historyQuery.data?.days.map((dayGroup) => (
              <DayCard
                key={dayGroup.date}
                dayGroup={dayGroup}
                onStartChat={handleStartChat}
                onInspiration={handleInspiration}
              />
            ))}
          </div>
          {historyQuery.data && historyQuery.data.days.length === 0 && (
            <EmptyState onRefresh={handleRefresh} message="暂无历史热点数据，系统每30分钟自动采集" />
          )}
        </>
      )}
    </div>
  )
}

function EmptyState({ onRefresh, message = '暂无热点数据' }: { onRefresh: () => void; message?: string }) {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <Flame className="h-12 w-12 mx-auto mb-3 opacity-30" />
      <p>{message}</p>
      <Separator className="my-4 max-w-xs mx-auto" />
      <Button variant="outline" onClick={onRefresh}>
        刷新试试
      </Button>
    </div>
  )
}
