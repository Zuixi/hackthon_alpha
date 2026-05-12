import { useState, useMemo } from 'react'
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
  Search,
  LayoutGrid,
  Layers,
  Tags,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import type {
  HotTopic,
  HotDayGroup,
  PlatformInfo,
  KeywordGroupResponse,
} from '@/types/api'

type ViewMode = 'all' | 'platform' | 'topic' | 'history'

const PLATFORM_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  zhihu:     { bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200' },
  weibo:     { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200' },
  douyin:    { bg: 'bg-zinc-50',    text: 'text-zinc-800',    border: 'border-zinc-300' },
  bilibili:  { bg: 'bg-cyan-50',    text: 'text-cyan-700',    border: 'border-cyan-200' },
  baidu:     { bg: 'bg-indigo-50',  text: 'text-indigo-700',  border: 'border-indigo-200' },
  toutiao:   { bg: 'bg-rose-50',    text: 'text-rose-700',    border: 'border-rose-200' },
  thepaper:  { bg: 'bg-slate-50',   text: 'text-slate-700',   border: 'border-slate-300' },
  tieba:     { bg: 'bg-sky-50',     text: 'text-sky-700',     border: 'border-sky-200' },
}

const TOP3_COLORS = [
  'bg-red-500 text-white',
  'bg-orange-500 text-white',
  'bg-amber-500 text-white',
]

function getPlatformStyle(platformId: string) {
  return PLATFORM_COLORS[platformId] ?? { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' }
}

function PlatformBadge({ platformId, platformName }: { platformId: string; platformName: string }) {
  const style = getPlatformStyle(platformId)
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${style.bg} ${style.text} ${style.border}`}>
      {platformName}
    </span>
  )
}

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
  showPlatform = false,
}: {
  topic: HotTopic
  index: number
  onStartChat: (topic: HotTopic) => void
  onInspiration: (topic: HotTopic) => void
  showPlatform?: boolean
}) {
  return (
    <div className="group flex items-start gap-3 py-2.5 px-2 rounded-lg hover:bg-muted/50 transition-colors">
      <span
        className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
          index < 3 ? TOP3_COLORS[index] : 'bg-muted text-muted-foreground'
        }`}
      >
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {showPlatform && (
            <PlatformBadge platformId={topic.platform} platformName={topic.platform_name} />
          )}
          <h4 className="text-sm font-medium text-foreground leading-snug truncate">
            {topic.title}
          </h4>
        </div>
        {topic.excerpt && (
          <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
            {topic.excerpt}
          </p>
        )}
      </div>
      <div className="flex-shrink-0 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button size="sm" variant="default" className="h-6 text-[11px] px-2" onClick={() => onStartChat(topic)}>
          <MessageSquare className="h-3 w-3 mr-0.5" />
          创作
        </Button>
        <Button size="sm" variant="outline" className="h-6 text-[11px] px-2" onClick={() => onInspiration(topic)}>
          <Lightbulb className="h-3 w-3 mr-0.5" />
          灵感
        </Button>
        {topic.url && (
          <a
            href={topic.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-6 w-6 rounded-md text-muted-foreground hover:bg-muted transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  )
}

function PlatformChips({
  platforms,
  selected,
  onToggle,
}: {
  platforms: PlatformInfo[]
  selected: Set<string>
  onToggle: (id: string) => void
}) {
  const isAll = selected.size === 0
  return (
    <div className="flex flex-wrap gap-1.5">
      <button
        onClick={() => onToggle('__all__')}
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
          isAll
            ? 'bg-foreground text-background border-foreground'
            : 'bg-background text-muted-foreground border-border hover:border-foreground/30'
        }`}
      >
        全部
      </button>
      {platforms.map((p) => {
        const active = selected.has(p.id)
        const style = getPlatformStyle(p.id)
        return (
          <button
            key={p.id}
            onClick={() => onToggle(p.id)}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
              active
                ? `${style.bg} ${style.text} ${style.border}`
                : 'bg-background text-muted-foreground border-border hover:border-foreground/30'
            }`}
          >
            {p.name}
            <span className="text-[10px] opacity-60">{p.count}</span>
          </button>
        )
      })}
    </div>
  )
}

function PlatformGroupCard({
  platform,
  topics,
  onStartChat,
  onInspiration,
}: {
  platform: PlatformInfo
  topics: HotTopic[]
  onStartChat: (topic: HotTopic) => void
  onInspiration: (topic: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const style = getPlatformStyle(platform.id)

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}>
              {platform.name}
            </span>
            <span className="text-muted-foreground text-xs font-normal">
              {topics.length} 条热点
            </span>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-2">
          <div className="divide-y divide-border/50">
            {topics.map((topic, idx) => (
              <TopicItem
                key={topic.id}
                topic={topic}
                index={idx}
                onStartChat={onStartChat}
                onInspiration={onInspiration}
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

function KeywordGroupCard({
  group,
  onStartChat,
  onInspiration,
}: {
  group: KeywordGroupResponse
  onStartChat: (topic: HotTopic) => void
  onInspiration: (topic: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Tags className="h-4 w-4 text-orange-500" />
            {group.display_name}
            <Badge variant="secondary" className="text-[10px] font-normal">
              {group.count} 条
            </Badge>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-2">
          <div className="divide-y divide-border/50">
            {group.topics.map((topic, idx) => (
              <TopicItem
                key={topic.id}
                topic={topic}
                index={idx}
                onStartChat={onStartChat}
                onInspiration={onInspiration}
                showPlatform
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
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
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Calendar className="h-4 w-4 text-blue-500" />
            {formatDate(dayGroup.date)}
            <Badge variant="secondary" className="text-[10px] font-normal">
              {dayGroup.topic_count} 条热点
            </Badge>
            <Badge variant="outline" className="text-[10px] font-normal">
              {dayGroup.batches.length} 次更新
            </Badge>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-2">
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
                    showPlatform
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

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="space-y-3">
              <Skeleton className="h-5 w-1/3" />
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex items-start gap-3">
                  <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
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
  )
}

function EmptyState({ onRefresh, message = '暂无热点数据' }: { onRefresh: () => void; message?: string }) {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <Flame className="h-12 w-12 mx-auto mb-3 opacity-30" />
      <p>{message}</p>
      <Separator className="my-4 max-w-xs mx-auto" />
      <Button variant="outline" onClick={onRefresh}>刷新试试</Button>
    </div>
  )
}

const VIEW_TABS: { id: ViewMode; label: string; icon: typeof TrendingUp }[] = [
  { id: 'all', label: '全部', icon: TrendingUp },
  { id: 'platform', label: '按平台', icon: LayoutGrid },
  { id: 'topic', label: '按主题', icon: Tags },
  { id: 'history', label: '历史', icon: Calendar },
]

export function HotPage() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>('all')
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')

  const platformFilter = selectedPlatforms.size > 0 ? [...selectedPlatforms].join(',') : undefined

  const platformsQuery = useQuery({
    queryKey: ['hot-platforms'],
    queryFn: () => api.hot.platforms(),
    staleTime: 60_000,
  })

  const latestQuery = useQuery({
    queryKey: ['hot-topics', platformFilter],
    queryFn: () => api.hot.list({ limit: 100, platform: platformFilter }),
    staleTime: 60_000,
    enabled: viewMode === 'all' || viewMode === 'platform',
  })

  const groupedQuery = useQuery({
    queryKey: ['hot-grouped', platformFilter],
    queryFn: () => api.hot.grouped(platformFilter),
    staleTime: 60_000,
    enabled: viewMode === 'topic',
  })

  const historyQuery = useQuery({
    queryKey: ['hot-history', platformFilter],
    queryFn: () => api.hot.history(5, platformFilter),
    staleTime: 120_000,
    enabled: viewMode === 'history',
  })

  const isLoading = (() => {
    switch (viewMode) {
      case 'all':
      case 'platform':
        return latestQuery.isLoading
      case 'topic':
        return groupedQuery.isLoading
      case 'history':
        return historyQuery.isLoading
    }
  })()

  const isFetching = (() => {
    switch (viewMode) {
      case 'all':
      case 'platform':
        return latestQuery.isFetching
      case 'topic':
        return groupedQuery.isFetching
      case 'history':
        return historyQuery.isFetching
    }
  })()

  const handleRefresh = () => {
    platformsQuery.refetch()
    switch (viewMode) {
      case 'all':
      case 'platform':
        latestQuery.refetch()
        break
      case 'topic':
        groupedQuery.refetch()
        break
      case 'history':
        historyQuery.refetch()
        break
    }
  }

  const handleTogglePlatform = (id: string) => {
    if (id === '__all__') {
      setSelectedPlatforms(new Set())
      return
    }
    setSelectedPlatforms((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
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

  const filteredTopics = useMemo(() => {
    const items = latestQuery.data?.items ?? []
    if (!searchQuery.trim()) return items
    const q = searchQuery.toLowerCase()
    return items.filter((t) => t.title.toLowerCase().includes(q))
  }, [latestQuery.data, searchQuery])

  const platformGroupedTopics = useMemo(() => {
    const items = filteredTopics
    const grouped: Record<string, HotTopic[]> = {}
    for (const topic of items) {
      const key = topic.platform
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(topic)
    }
    return grouped
  }, [filteredTopics])

  const platforms = platformsQuery.data?.platforms ?? []

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            热点广场
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            多平台实时热点聚合 · 每30分钟自动更新
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border bg-muted p-0.5">
            {VIEW_TABS.map(({ id, label, icon: Icon }) => (
              <Button
                key={id}
                variant={viewMode === id ? 'default' : 'ghost'}
                size="sm"
                className="h-7 text-[11px] gap-1 px-2"
                onClick={() => setViewMode(id)}
              >
                <Icon className="h-3 w-3" />
                <span className="hidden sm:inline">{label}</span>
              </Button>
            ))}
          </div>
          <Button variant="outline" size="sm" className="h-7" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      {viewMode !== 'history' && platforms.length > 0 && (
        <div className="mb-4 space-y-2">
          <PlatformChips
            platforms={platforms}
            selected={selectedPlatforms}
            onToggle={handleTogglePlatform}
          />
          {(viewMode === 'all' || viewMode === 'platform') && (
            <div className="relative max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="搜索热点标题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 text-xs pl-8 pr-8"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Stats bar */}
      {!isLoading && viewMode !== 'history' && (
        <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
          {viewMode === 'all' && latestQuery.data && (
            <span>共 {filteredTopics.length} 条热点 · {platforms.length} 个平台</span>
          )}
          {viewMode === 'platform' && latestQuery.data && (
            <span>共 {filteredTopics.length} 条热点 · {Object.keys(platformGroupedTopics).length} 个平台</span>
          )}
          {viewMode === 'topic' && groupedQuery.data && (
            <span>共 {groupedQuery.data.total} 条热点 · {groupedQuery.data.groups.length} 个主题分组</span>
          )}
        </div>
      )}

      {/* Loading */}
      {isLoading && <LoadingSkeleton />}

      {/* ALL view */}
      {!isLoading && viewMode === 'all' && (
        <>
          {filteredTopics.length > 0 ? (
            <div className="space-y-0.5">
              {filteredTopics.map((topic, index) => (
                <div key={topic.id} className="group hover:bg-muted/30 rounded-lg transition-colors">
                  <TopicItem
                    topic={topic}
                    index={index}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                    showPlatform
                  />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState onRefresh={handleRefresh} />
          )}
        </>
      )}

      {/* PLATFORM view */}
      {!isLoading && viewMode === 'platform' && (
        <>
          {Object.keys(platformGroupedTopics).length > 0 ? (
            <div className="space-y-3">
              {platforms
                .filter((p) => platformGroupedTopics[p.id]?.length)
                .map((p) => (
                  <PlatformGroupCard
                    key={p.id}
                    platform={p}
                    topics={platformGroupedTopics[p.id]}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                  />
                ))}
            </div>
          ) : (
            <EmptyState onRefresh={handleRefresh} />
          )}
        </>
      )}

      {/* TOPIC view */}
      {!isLoading && viewMode === 'topic' && (
        <>
          {groupedQuery.data && groupedQuery.data.groups.length > 0 ? (
            <div className="space-y-3">
              {groupedQuery.data.groups.map((group) => (
                <KeywordGroupCard
                  key={group.group_name}
                  group={group}
                  onStartChat={handleStartChat}
                  onInspiration={handleInspiration}
                />
              ))}
              {groupedQuery.data.unmatched.length > 0 && (
                <Card className="overflow-hidden">
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                      <Layers className="h-4 w-4" />
                      其他热点
                      <Badge variant="outline" className="text-[10px] font-normal">
                        {groupedQuery.data.unmatched.length} 条
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 pb-2 px-2">
                    <div className="divide-y divide-border/50">
                      {groupedQuery.data.unmatched.slice(0, 30).map((topic, idx) => (
                        <TopicItem
                          key={topic.id}
                          topic={topic}
                          index={idx}
                          onStartChat={handleStartChat}
                          onInspiration={handleInspiration}
                          showPlatform
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <EmptyState onRefresh={handleRefresh} message="暂无主题分组数据，请检查关键词规则配置" />
          )}
        </>
      )}

      {/* HISTORY view */}
      {!isLoading && viewMode === 'history' && (
        <>
          {historyQuery.data && historyQuery.data.days.length > 0 ? (
            <>
              <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
                <span>最近 {historyQuery.data.total_days} 天的热榜记录</span>
              </div>
              <div className="space-y-3">
                {historyQuery.data.days.map((dayGroup) => (
                  <DayCard
                    key={dayGroup.date}
                    dayGroup={dayGroup}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                  />
                ))}
              </div>
            </>
          ) : (
            <EmptyState onRefresh={handleRefresh} message="暂无历史热点数据，系统每30分钟自动采集" />
          )}
        </>
      )}
    </div>
  )
}
