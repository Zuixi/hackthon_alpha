import { useState, useMemo, useCallback } from 'react'
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
  TrendingDown,
  Calendar,
  ChevronDown,
  ChevronUp,
  Search,
  LayoutGrid,
  LayoutList,
  Layers,
  Tags,
  X,
  Sparkles,
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
type LayoutMode = 'list' | 'card'

// ─── Visual tokens ───────────────────────────────────────────────────────────

const PLATFORM_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  zhihu:     { bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200',   dot: 'bg-[#0066ff]' },
  weibo:     { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200',    dot: 'bg-[#ea0000]' },
  douyin:    { bg: 'bg-zinc-100',   text: 'text-zinc-800',    border: 'border-zinc-300',   dot: 'bg-zinc-900' },
  bilibili:  { bg: 'bg-pink-50',   text: 'text-pink-700',    border: 'border-pink-200',   dot: 'bg-[#fb7299]' },
  baidu:     { bg: 'bg-indigo-50',  text: 'text-indigo-700',  border: 'border-indigo-200', dot: 'bg-[#2932e1]' },
  toutiao:   { bg: 'bg-rose-50',    text: 'text-rose-700',    border: 'border-rose-200',   dot: 'bg-rose-600' },
  thepaper:  { bg: 'bg-slate-50',   text: 'text-slate-700',   border: 'border-slate-300',  dot: 'bg-slate-600' },
  tieba:     { bg: 'bg-sky-50',     text: 'text-sky-700',     border: 'border-sky-200',    dot: 'bg-sky-600' },
}

function getRankStyle(rank: number): { bg: string; text: string; ring?: string } {
  if (rank === 1) return { bg: 'bg-red-500',    text: 'text-white',              ring: 'ring-red-200' }
  if (rank === 2) return { bg: 'bg-orange-500',  text: 'text-white',              ring: 'ring-orange-200' }
  if (rank === 3) return { bg: 'bg-amber-500',   text: 'text-white',              ring: 'ring-amber-200' }
  if (rank <= 5)  return { bg: 'bg-gray-600',    text: 'text-white' }
  if (rank <= 7)  return { bg: 'bg-gray-400',    text: 'text-white' }
  if (rank <= 10) return { bg: 'bg-gray-300',    text: 'text-gray-700' }
  return                  { bg: 'bg-gray-100',    text: 'text-gray-500' }
}

type TopicStatus = 'new' | 'rising' | 'hot' | 'falling' | 'normal'

const STATUS_CONFIG: Record<TopicStatus, { label: string; bg: string; text: string; icon: typeof TrendingUp | null; pulse?: boolean }> = {
  new:     { label: '新上榜',   bg: 'bg-emerald-50',  text: 'text-emerald-700', icon: Sparkles,     pulse: true },
  rising:  { label: '热度飙升', bg: 'bg-red-50',      text: 'text-red-700',     icon: TrendingUp },
  hot:     { label: '持续高热', bg: 'bg-amber-50',    text: 'text-amber-700',   icon: Flame },
  falling: { label: '下降中',   bg: 'bg-gray-100',    text: 'text-gray-500',    icon: TrendingDown },
  normal:  { label: '',         bg: '',                text: '',                  icon: null },
}

// ─── Utilities ───────────────────────────────────────────────────────────────

function getPlatformStyle(id: string) {
  return PLATFORM_COLORS[id] ?? { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200', dot: 'bg-gray-400' }
}

function formatHeatValue(score: number): string {
  if (!score || score <= 0) return ''
  if (score >= 100_000_000) return `${(score / 100_000_000).toFixed(1)}亿`
  if (score >= 10_000) return `${(score / 10_000).toFixed(score >= 100_000 ? 0 : 1)}w`
  return score.toLocaleString()
}

function getMockHeatValue(index: number): number {
  const base = Math.max(500_000 - index * 35_000, 8_000)
  const jitter = ((index * 7 + 13) % 23) * 1_000
  return base + jitter
}

function getMockStatus(index: number): TopicStatus {
  if (index < 2) return 'hot'
  if (index < 5) return 'rising'
  if (index % 7 === 0) return 'new'
  if (index > 15 && index % 4 === 0) return 'falling'
  return 'normal'
}

function generateMockTrend(index: number): number[] {
  const seed = index * 17 + 3
  return Array.from({ length: 7 }, (_, i) => {
    const base = Math.sin((seed + i) * 0.7) * 0.3 + 0.5
    return Math.max(0.05, Math.min(1, base + ((seed * (i + 1)) % 17) / 50))
  })
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

// ─── Small UI Components ─────────────────────────────────────────────────────

function RankBadge({ rank }: { rank: number }) {
  const style = getRankStyle(rank)
  return (
    <span
      className={`flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold tabular-nums ${style.bg} ${style.text} ${style.ring ? `ring-2 ${style.ring}` : ''}`}
    >
      {rank}
    </span>
  )
}

function PlatformTag({ platformId, platformName }: { platformId: string; platformName: string }) {
  const style = getPlatformStyle(platformId)
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${style.bg} ${style.text} ${style.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {platformName}
    </span>
  )
}

function StatusBadge({ status }: { status: TopicStatus }) {
  if (status === 'normal') return null
  const cfg = STATUS_CONFIG[status]
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold ${cfg.bg} ${cfg.text} ${cfg.pulse ? 'animate-pulse' : ''}`}>
      {Icon && <Icon className="w-2.5 h-2.5" />}
      {cfg.label}
    </span>
  )
}

function Sparkline({ data, status }: { data: number[]; status: TopicStatus }) {
  if (!data.length) return null
  const w = 56
  const h = 22
  const padY = 2
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - padY - ((v - min) / range) * (h - padY * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const lastX = w
  const lastY = h - padY - ((data[data.length - 1] - min) / range) * (h - padY * 2)

  const color =
    status === 'rising' || status === 'new' ? '#22c55e'
    : status === 'hot' ? '#f97316'
    : '#9ca3af'

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="flex-shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="2" fill={color} />
    </svg>
  )
}

// ─── Hotspot Row (List View) ─────────────────────────────────────────────────

function HotspotRow({
  topic,
  rank,
  onStartChat,
  onInspiration,
  showPlatform = false,
}: {
  topic: HotTopic
  rank: number
  onStartChat: (t: HotTopic) => void
  onInspiration: (t: HotTopic) => void
  showPlatform?: boolean
}) {
  const status = getMockStatus(rank - 1)
  const trend = generateMockTrend(rank - 1)
  const effectiveScore = topic.hot_score > 0 ? topic.hot_score : getMockHeatValue(rank - 1)
  const heatStr = formatHeatValue(effectiveScore)

  return (
    <div className="group flex items-center gap-4 px-5 py-3.5 rounded-xl hover:bg-muted/60 transition-all duration-200 cursor-pointer">
      {/* L1: Rank */}
      <RankBadge rank={rank} />

      {/* L2-L4: Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
          {showPlatform && <PlatformTag platformId={topic.platform} platformName={topic.platform_name} />}
          <StatusBadge status={status} />
        </div>
        <h4
          className="text-[15px] font-medium text-foreground leading-snug truncate"
          title={topic.title}
        >
          {topic.title}
        </h4>
        {topic.excerpt && (
          <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{topic.excerpt}</p>
        )}
      </div>

      {/* L5: Heat + Sparkline */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="flex flex-col items-end gap-0.5">
          <span className="text-sm font-semibold text-foreground tabular-nums">{heatStr}</span>
          <Sparkline data={trend} status={status} />
        </div>

        {/* L6: Action Group — hover reveal */}
        <div className="flex items-center gap-1 pl-3 border-l border-gray-100 opacity-0 translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200">
          <button
            onClick={(e) => { e.stopPropagation(); onInspiration(topic) }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium bg-amber-50 text-amber-800 hover:bg-amber-100 transition-colors"
            title="记录灵感"
          >
            <Lightbulb className="w-3 h-3" />
            <span className="hidden lg:inline">灵感</span>
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onStartChat(topic) }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
            title="创作对话"
          >
            <MessageSquare className="w-3 h-3" />
            <span className="hidden lg:inline">创作</span>
          </button>
          {topic.url && (
            <a
              href={topic.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center justify-center w-6 h-6 rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              title="查看原帖"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Hotspot Card (Card View) ────────────────────────────────────────────────

function HotspotCard({
  topic,
  rank,
  onStartChat,
  onInspiration,
}: {
  topic: HotTopic
  rank: number
  onStartChat: (t: HotTopic) => void
  onInspiration: (t: HotTopic) => void
}) {
  const status = getMockStatus(rank - 1)
  const trend = generateMockTrend(rank - 1)
  const effectiveScore = topic.hot_score > 0 ? topic.hot_score : getMockHeatValue(rank - 1)
  const heatStr = formatHeatValue(effectiveScore)

  return (
    <div className="group flex flex-col gap-2.5 p-4 rounded-xl border bg-card hover:shadow-md hover:border-gray-200 transition-all duration-200 cursor-pointer">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RankBadge rank={rank} />
          <PlatformTag platformId={topic.platform} platformName={topic.platform_name} />
        </div>
        <StatusBadge status={status} />
      </div>

      <h4 className="text-[15px] font-medium text-foreground leading-snug line-clamp-2" title={topic.title}>
        {topic.title}
      </h4>

      {topic.excerpt && (
        <p className="text-xs text-muted-foreground line-clamp-2">{topic.excerpt}</p>
      )}

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground tabular-nums">{heatStr}</span>
          <Sparkline data={trend} status={status} />
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); onInspiration(topic) }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium bg-amber-50 text-amber-800 hover:bg-amber-100 transition-colors"
          >
            <Lightbulb className="w-3 h-3" />
            灵感
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onStartChat(topic) }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
          >
            <MessageSquare className="w-3 h-3" />
            创作
          </button>
          {topic.url && (
            <a
              href={topic.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center justify-center w-6 h-6 rounded-md text-gray-500 hover:bg-gray-100 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Platform Chips (Filter Bar) ─────────────────────────────────────────────

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
    <div className="overflow-x-auto sm:overflow-visible pb-1">
      <div className="flex items-center gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
        {/* All button */}
        <button
          onClick={() => onToggle('__all__')}
          className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-150 ${
            isAll
              ? 'bg-foreground text-background border-foreground shadow-sm'
              : 'bg-background text-muted-foreground border-border hover:border-foreground/30 hover:text-foreground'
          }`}
        >
          全部
        </button>

        {/* Platform capsules */}
        {platforms.map((p) => {
          const active = selected.has(p.id)
          const style = getPlatformStyle(p.id)
          return (
            <button
              key={p.id}
              onClick={() => onToggle(p.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-150 ${
                active
                  ? `${style.bg} ${style.text} ${style.border} shadow-sm`
                  : 'bg-background text-muted-foreground border-border hover:border-foreground/30 hover:text-foreground'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${active ? style.dot : 'bg-gray-300'}`} />
              {p.name}
              <span className="text-[10px] opacity-50 tabular-nums">{p.count}</span>
            </button>
          )
        })}

        {/* Selected count indicator */}
        {selected.size > 0 && (
          <button
            onClick={() => onToggle('__all__')}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-3 h-3" />
            清除筛选
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Grouped Cards (Platform / Keyword / Day) ────────────────────────────────

function PlatformGroupCard({
  platform,
  topics,
  onStartChat,
  onInspiration,
}: {
  platform: PlatformInfo
  topics: HotTopic[]
  onStartChat: (t: HotTopic) => void
  onInspiration: (t: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const style = getPlatformStyle(platform.id)

  return (
    <Card className="overflow-hidden border-l-2" style={{ borderLeftColor: `var(--color-${platform.id}, #e5e7eb)` }}>
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-5"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              {platform.name}
            </span>
            <span className="text-muted-foreground text-xs font-normal tabular-nums">
              {topics.length} 条热点
            </span>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-1">
          {topics.map((topic, idx) => (
            <HotspotRow
              key={topic.id}
              topic={topic}
              rank={idx + 1}
              onStartChat={onStartChat}
              onInspiration={onInspiration}
            />
          ))}
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
  onStartChat: (t: HotTopic) => void
  onInspiration: (t: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-5"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Tags className="h-4 w-4 text-orange-500" />
            {group.display_name}
            <Badge variant="secondary" className="text-[10px] font-normal tabular-nums">
              {group.count} 条
            </Badge>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-1">
          {group.topics.map((topic, idx) => (
            <HotspotRow
              key={topic.id}
              topic={topic}
              rank={idx + 1}
              onStartChat={onStartChat}
              onInspiration={onInspiration}
              showPlatform
            />
          ))}
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
  onStartChat: (t: HotTopic) => void
  onInspiration: (t: HotTopic) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const latestBatch = dayGroup.batches[0]
  if (!latestBatch) return null

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors py-3 px-5"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Calendar className="h-4 w-4 text-blue-500" />
            {formatDate(dayGroup.date)}
            <Badge variant="secondary" className="text-[10px] font-normal tabular-nums">
              {dayGroup.topic_count} 条热点
            </Badge>
            <Badge variant="outline" className="text-[10px] font-normal tabular-nums">
              {dayGroup.batches.length} 次更新
            </Badge>
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 pb-2 px-1">
          {dayGroup.batches.map((batch) => (
            <div key={batch.fetch_batch} className="mb-3 last:mb-0">
              <div className="flex items-center gap-2 mb-1 px-5">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium tabular-nums">
                  {formatBatchTime(batch.fetch_batch)} 更新 · {batch.count} 条
                </span>
              </div>
              {batch.items.map((topic, idx) => (
                <HotspotRow
                  key={topic.id}
                  topic={topic}
                  rank={idx + 1}
                  onStartChat={onStartChat}
                  onInspiration={onInspiration}
                  showPlatform
                />
              ))}
              {batch !== dayGroup.batches[dayGroup.batches.length - 1] && (
                <Separator className="my-2 mx-5" />
              )}
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  )
}

// ─── Loading & Empty States ──────────────────────────────────────────────────

function LoadingSkeleton({ layout = 'list' }: { layout?: LayoutMode }) {
  if (layout === 'card') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-xl border p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-7 w-7 rounded-md" />
              <Skeleton className="h-4 w-16 rounded" />
            </div>
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="flex items-center justify-between pt-2 border-t border-gray-50">
              <Skeleton className="h-4 w-12" />
              <div className="flex gap-1">
                <Skeleton className="h-6 w-14 rounded-md" />
                <Skeleton className="h-6 w-14 rounded-md" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-3.5 rounded-xl">
          <Skeleton className="h-7 w-7 rounded-md flex-shrink-0" />
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Skeleton className="h-4 w-14 rounded" />
              <Skeleton className="h-4 w-12 rounded" />
            </div>
            <Skeleton className="h-5 w-3/4" />
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0">
            <Skeleton className="h-4 w-10" />
            <Skeleton className="h-5 w-14" />
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ onRefresh, message = '暂无热点数据' }: { onRefresh: () => void; message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-gray-50 flex items-center justify-center mb-4">
        <Flame className="h-8 w-8 text-gray-300" />
      </div>
      <p className="text-sm font-medium text-foreground mb-1">{message}</p>
      <p className="text-xs text-muted-foreground mb-6">试试切换其他平台或查看历史热点</p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          刷新数据
        </Button>
      </div>
    </div>
  )
}

// ─── View Tabs ───────────────────────────────────────────────────────────────

const VIEW_TABS: { id: ViewMode; label: string; icon: typeof TrendingUp }[] = [
  { id: 'all', label: '全部', icon: TrendingUp },
  { id: 'platform', label: '按平台', icon: LayoutGrid },
  { id: 'topic', label: '按主题', icon: Tags },
  { id: 'history', label: '历史', icon: Calendar },
]

// ─── Main Page ───────────────────────────────────────────────────────────────

export function HotPage() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>('all')
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('card')
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')

  const platformFilter = selectedPlatforms.size > 0 ? [...selectedPlatforms].join(',') : undefined

  const toggleLayout = useCallback((mode: LayoutMode) => {
    setLayoutMode(mode)
  }, [])

  // ── Queries ──

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

  // ── Derived State ──

  const isLoading = (() => {
    switch (viewMode) {
      case 'all':
      case 'platform': return latestQuery.isLoading
      case 'topic': return groupedQuery.isLoading
      case 'history': return historyQuery.isLoading
    }
  })()

  const isFetching = (() => {
    switch (viewMode) {
      case 'all':
      case 'platform': return latestQuery.isFetching
      case 'topic': return groupedQuery.isFetching
      case 'history': return historyQuery.isFetching
    }
  })()

  const handleRefresh = () => {
    platformsQuery.refetch()
    switch (viewMode) {
      case 'all':
      case 'platform': latestQuery.refetch(); break
      case 'topic': groupedQuery.refetch(); break
      case 'history': historyQuery.refetch(); break
    }
  }

  const handleTogglePlatform = (id: string) => {
    if (id === '__all__') {
      setSelectedPlatforms(new Set())
      return
    }
    setSelectedPlatforms((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
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
    const grouped: Record<string, HotTopic[]> = {}
    for (const topic of filteredTopics) {
      const key = topic.platform
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(topic)
    }
    return grouped
  }, [filteredTopics])

  const platforms = platformsQuery.data?.platforms ?? []

  const lastUpdated = useMemo(() => {
    const items = latestQuery.data?.items
    if (!items?.length) return null
    const batch = items[0].fetch_batch
    return batch ? formatBatchTime(batch) : null
  }, [latestQuery.data])

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
              <Flame className="h-4 w-4 text-white" />
            </div>
            热点广场
          </h2>
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
            多平台实时热点聚合 · 每30分钟自动更新
            {lastUpdated && (
              <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-muted tabular-nums">
                <Clock className="w-2.5 h-2.5" />
                {lastUpdated}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode tabs */}
          <div className="flex rounded-lg border bg-muted/50 p-0.5">
            {VIEW_TABS.map(({ id, label, icon: Icon }) => (
              <Button
                key={id}
                variant={viewMode === id ? 'default' : 'ghost'}
                size="sm"
                className={`h-7 text-[11px] gap-1 px-2.5 ${viewMode === id ? 'shadow-sm' : ''}`}
                onClick={() => setViewMode(id)}
              >
                <Icon className="h-3 w-3" />
                <span className="hidden sm:inline">{label}</span>
              </Button>
            ))}
          </div>

          {/* Layout toggle — only for all/platform views */}
          {(viewMode === 'all') && (
            <div className="flex rounded-md border bg-muted/50 p-0.5">
              <button
                onClick={() => toggleLayout('list')}
                className={`p-1 rounded-sm transition-colors ${layoutMode === 'list' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                title="列表视图"
              >
                <LayoutList className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => toggleLayout('card')}
                className={`p-1 rounded-sm transition-colors ${layoutMode === 'card' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                title="卡片视图"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Refresh */}
          <Button variant="outline" size="sm" className="h-7 w-7 p-0" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* ── Filter Bar ── */}
      {viewMode !== 'history' && platforms.length > 0 && (
        <div className="mb-4 space-y-2.5">
          <PlatformChips
            platforms={platforms}
            selected={selectedPlatforms}
            onToggle={handleTogglePlatform}
          />
          {(viewMode === 'all' || viewMode === 'platform') && (
            <div className="relative max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="搜索热点标题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 text-xs pl-9 pr-8 rounded-lg focus-visible:ring-2 focus-visible:ring-foreground/20"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Stats Bar ── */}
      {!isLoading && viewMode !== 'history' && (
        <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
          {(viewMode === 'all' || viewMode === 'platform') && latestQuery.data && (
            <span className="tabular-nums">共 {filteredTopics.length} 条热点 · {platforms.length} 个平台</span>
          )}
          {viewMode === 'topic' && groupedQuery.data && (
            <span className="tabular-nums">共 {groupedQuery.data.total} 条热点 · {groupedQuery.data.groups.length} 个主题分组</span>
          )}
        </div>
      )}

      {/* ── Loading ── */}
      {isLoading && <LoadingSkeleton layout={viewMode === 'all' ? layoutMode : 'list'} />}

      {/* ── ALL view ── */}
      {!isLoading && viewMode === 'all' && (
        <>
          {filteredTopics.length > 0 ? (
            layoutMode === 'card' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredTopics.map((topic, index) => (
                  <HotspotCard
                    key={topic.id}
                    topic={topic}
                    rank={index + 1}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredTopics.map((topic, index) => (
                  <HotspotRow
                    key={topic.id}
                    topic={topic}
                    rank={index + 1}
                    onStartChat={handleStartChat}
                    onInspiration={handleInspiration}
                    showPlatform
                  />
                ))}
              </div>
            )
          ) : (
            <EmptyState onRefresh={handleRefresh} />
          )}
        </>
      )}

      {/* ── PLATFORM view ── */}
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

      {/* ── TOPIC view ── */}
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
                  <CardHeader className="py-3 px-5">
                    <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                      <Layers className="h-4 w-4" />
                      其他热点
                      <Badge variant="outline" className="text-[10px] font-normal tabular-nums">
                        {groupedQuery.data.unmatched.length} 条
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 pb-2 px-1">
                    {groupedQuery.data.unmatched.slice(0, 30).map((topic, idx) => (
                      <HotspotRow
                        key={topic.id}
                        topic={topic}
                        rank={idx + 1}
                        onStartChat={handleStartChat}
                        onInspiration={handleInspiration}
                        showPlatform
                      />
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <EmptyState onRefresh={handleRefresh} message="暂无主题分组数据，请检查关键词规则配置" />
          )}
        </>
      )}

      {/* ── HISTORY view ── */}
      {!isLoading && viewMode === 'history' && (
        <>
          {historyQuery.data && historyQuery.data.days.length > 0 ? (
            <>
              <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
                <span className="tabular-nums">最近 {historyQuery.data.total_days} 天的热榜记录</span>
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
