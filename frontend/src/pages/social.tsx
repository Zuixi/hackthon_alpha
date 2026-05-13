import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Users,
  Activity,
  RefreshCw,
  UserCircle,
  ExternalLink,
  Clock,
  UserPlus,
  TrendingUp,
  TrendingDown,
  BarChart2,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { api } from '@/lib/api'
import type { Followee, Moment, FollowerSnapshotItem } from '@/types/api'

type TabId = 'followers' | 'followees' | 'moments'

const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
  { id: 'followers', label: '粉丝列表', icon: UserPlus },
  { id: 'followees', label: '关注列表', icon: Users },
  { id: 'moments', label: '关注动态', icon: Activity },
]

function formatTimestamp(ts: number): string {
  if (!ts) return ''
  const date = new Date(ts * 1000)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60_000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`

  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`

  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 30) return `${diffDay} 天前`

  return date.toLocaleDateString('zh-CN')
}

function SnapshotDelta({ item }: { item: FollowerSnapshotItem }) {
  if (item.delta === null || item.delta === 0) {
    return <span className="text-xs text-slate-400">持平</span>
  }
  if (item.delta > 0) {
    return (
      <span className="text-xs text-green-600 inline-flex items-center gap-0.5 font-medium">
        <TrendingUp className="h-3 w-3" />+{item.delta}
      </span>
    )
  }
  return (
    <span className="text-xs text-red-500 inline-flex items-center gap-0.5 font-medium">
      <TrendingDown className="h-3 w-3" />
      {item.delta}
    </span>
  )
}

function PersonCard({ item }: { item: Followee }) {
  return (
    <div className="bg-white rounded-2xl p-4 md:p-5 border border-slate-100 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
      <div className="flex items-start gap-4">
        <div className="relative flex-shrink-0">
          <Avatar className="h-12 w-12">
            <AvatarImage src={item.avatar_path} />
            <AvatarFallback className="bg-slate-100">
              <UserCircle className="h-6 w-6 text-slate-400" />
            </AvatarFallback>
          </Avatar>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="font-bold text-slate-900 text-sm">{item.fullname}</h3>
            {item.gender && (
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] border border-slate-200">
                {item.gender === 'male' ? '男' : item.gender === 'female' ? '女' : item.gender}
              </span>
            )}
          </div>
          {item.headline && (
            <p className="text-xs text-slate-500 mb-0.5 line-clamp-1">{item.headline}</p>
          )}
          {item.description && (
            <p className="text-[11px] text-slate-400 line-clamp-1">{item.description}</p>
          )}
        </div>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 inline-flex items-center justify-center h-8 w-8 rounded-lg text-slate-400 hover:bg-violet-50 hover:text-violet-500 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>
    </div>
  )
}

function MomentCard({ item }: { item: Moment }) {
  return (
    <div className="bg-white rounded-2xl p-4 md:p-5 border border-slate-100 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
      <div className="flex items-start gap-3">
        <Avatar className="h-9 w-9 mt-0.5 flex-shrink-0">
          <AvatarFallback className="bg-violet-100 text-violet-600 text-xs font-bold">
            {item.actor.name?.[0] || '?'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-sm text-slate-900">{item.actor.name}</span>
            <span className="text-sm text-slate-500">{item.action_text}</span>
            {item.action_time > 0 && (
              <span className="text-xs text-slate-400 flex items-center gap-0.5 ml-auto">
                <Clock className="h-3 w-3" />
                {formatTimestamp(item.action_time)}
              </span>
            )}
          </div>
          {item.target && (
            <div className="mt-2 rounded-xl bg-slate-50 border border-slate-100 p-3">
              {item.target.title && (
                <h4 className="font-semibold text-sm text-slate-800 mb-1">{item.target.title}</h4>
              )}
              {item.target.excerpt && (
                <p className="text-xs text-slate-500 line-clamp-3">{item.target.excerpt}</p>
              )}
              {item.target.author?.name && (
                <p className="text-[11px] text-slate-400 mt-1.5">作者：{item.target.author.name}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Pagination({
  page,
  hasMore,
  onPrev,
  onNext,
}: {
  page: number
  hasMore: boolean
  onPrev: () => void
  onNext: () => void
}) {
  return (
    <div className="flex items-center justify-center gap-2 pt-4">
      <Button variant="outline" size="sm" disabled={page === 0} onClick={onPrev}>
        上一页
      </Button>
      <span className="text-sm text-slate-400 px-2">第 {page + 1} 页</span>
      <Button variant="outline" size="sm" disabled={!hasMore} onClick={onNext}>
        下一页
      </Button>
    </div>
  )
}

function PersonCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl p-4 border border-slate-100">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-full" />
        <div className="flex-1">
          <Skeleton className="h-4 w-28 mb-2" />
          <Skeleton className="h-3 w-44" />
        </div>
      </div>
    </div>
  )
}

function FollowersInsightCards({
  latestCount,
  snapshots,
  isLoading,
}: {
  latestCount: number | undefined
  snapshots: FollowerSnapshotItem[]
  isLoading: boolean
}) {
  const last7 = snapshots.slice(-7)
  const lastSnap = snapshots.at(-1)
  const maxCount = Math.max(...last7.map((s) => s.follower_count), 1)

  const growthDays = last7.filter((s) => (s.delta ?? 0) > 0).length
  const totalGrowth = last7.reduce((sum, s) => sum + (s.delta ?? 0), 0)

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Card 1: 粉丝总数 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-100 relative overflow-hidden group hover:-translate-y-1 transition-transform duration-200">
        <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/8 rounded-full blur-2xl -mr-8 -mt-8 pointer-events-none" />
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
            <Users className="w-4 h-4 text-amber-500" />
          </div>
          <span className="text-sm font-bold text-slate-700">粉丝总数</span>
        </div>
        {isLoading ? (
          <Skeleton className="h-8 w-24 mb-2" />
        ) : (
          <p className="text-3xl font-bold text-slate-900 mb-1">
            {latestCount ?? '--'}
          </p>
        )}
        <div className="flex items-center gap-1.5 mt-1">
          {lastSnap ? (
            <SnapshotDelta item={lastSnap} />
          ) : (
            <span className="text-xs text-slate-400">暂无对比数据</span>
          )}
          <span className="text-xs text-slate-400">较上次快照</span>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-50 flex items-center justify-between">
          <span className="text-[10px] text-slate-400">
            {lastSnap ? `最近记录：${lastSnap.snapshot_date}` : '等待首次记录'}
          </span>
          <span className="text-[10px] text-amber-500 font-medium">每日 20:00 更新</span>
        </div>
      </div>

      {/* Card 2: 近7日趋势 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-100 relative overflow-hidden group hover:-translate-y-1 transition-transform duration-200">
        <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/8 rounded-full blur-2xl -mr-8 -mt-8 pointer-events-none" />
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
            <BarChart2 className="w-4 h-4 text-violet-500" />
          </div>
          <span className="text-sm font-bold text-slate-700">近7日走势</span>
        </div>
        {isLoading ? (
          <div className="flex items-end gap-1 h-12">
            {Array.from({ length: 7 }).map((_, i) => (
              <Skeleton key={i} className="flex-1 rounded-sm" style={{ height: `${40 + i * 5}%` }} />
            ))}
          </div>
        ) : last7.length > 0 ? (
          <div className="flex items-end gap-1 h-12">
            {last7.map((s) => {
              const pct = Math.max(10, Math.round((s.follower_count / maxCount) * 100))
              return (
                <div key={s.snapshot_date} className="flex-1 group/bar relative" title={`${s.snapshot_date}: ${s.follower_count}`}>
                  <div
                    className="w-full bg-violet-500/20 hover:bg-violet-500/40 rounded-sm transition-colors cursor-default"
                    style={{ height: `${pct}%` }}
                  />
                </div>
              )
            })}
          </div>
        ) : (
          <div className="h-12 flex items-center justify-center">
            <span className="text-xs text-slate-400">暂无快照数据</span>
          </div>
        )}
        <div className="mt-3 pt-3 border-t border-slate-50 flex justify-between text-[10px] text-slate-400">
          <span>{last7.at(0)?.snapshot_date ?? '--'}</span>
          <span>{last7.at(-1)?.snapshot_date ?? '--'}</span>
        </div>
      </div>

      {/* Card 3: 增长概览 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-100 relative overflow-hidden group hover:-translate-y-1 transition-transform duration-200">
        <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/8 rounded-full blur-2xl -mr-8 -mt-8 pointer-events-none" />
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-cyan-500" />
          </div>
          <span className="text-sm font-bold text-slate-700">增长概览</span>
        </div>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-cyan-500 font-bold text-xs mt-0.5">①</span>
              <span className="text-slate-600 text-xs">
                近 7 天共
                <span className="font-bold text-slate-900 mx-1">{growthDays}</span>
                天净增粉丝
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-cyan-500 font-bold text-xs mt-0.5">②</span>
              <span className="text-slate-600 text-xs">
                7 天累计变化
                <span className={`font-bold mx-1 ${totalGrowth >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                  {totalGrowth >= 0 ? '+' : ''}{totalGrowth}
                </span>
                人
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-cyan-500 font-bold text-xs mt-0.5">③</span>
              <span className="text-slate-600 text-xs">
                已累计追踪
                <span className="font-bold text-slate-900 mx-1">{snapshots.length}</span>
                个快照
              </span>
            </div>
          </div>
        )}
        <div className="mt-3 pt-3 border-t border-slate-50">
          <p className="text-[10px] text-cyan-600 bg-cyan-50 rounded-lg px-2.5 py-1.5 leading-relaxed">
            💡 快照数据每日 20:00 自动记录，可追踪长期粉丝变化趋势
          </p>
        </div>
      </div>
    </div>
  )
}

function FollowersTab() {
  const [page, setPage] = useState(0)
  const perPage = 20
  const followersQuery = useQuery({
    queryKey: ['followers', page],
    queryFn: () => api.social.followers(page, perPage),
    staleTime: 5 * 60_000,
  })
  const statsQuery = useQuery({
    queryKey: ['followers-stats'],
    queryFn: () => api.social.followerStats(30),
    staleTime: 5 * 60_000,
  })

  const data = followersQuery.data
  const snapshots = statsQuery.data?.items ?? []
  const totalText =
    typeof data?.page.total === 'number'
      ? `共 ${data.page.total} 位粉丝`
      : `本页 ${data?.items.length ?? 0} 人`

  return (
    <div className="space-y-3">
      <FollowersInsightCards
        latestCount={statsQuery.data?.latest_count ?? undefined}
        snapshots={snapshots}
        isLoading={statsQuery.isLoading}
      />

      <div className="flex items-center justify-between mb-1">
        <p className="text-sm text-slate-400">{data ? totalText : '加载中...'}</p>
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-500 hover:text-slate-700"
          onClick={() => {
            followersQuery.refetch()
            statsQuery.refetch()
          }}
          disabled={followersQuery.isFetching || statsQuery.isFetching}
        >
          <RefreshCw
            className={`h-3.5 w-3.5 mr-1 ${followersQuery.isFetching || statsQuery.isFetching ? 'animate-spin' : ''}`}
          />
          刷新
        </Button>
      </div>

      {followersQuery.isLoading
        ? Array.from({ length: 5 }).map((_, i) => <PersonCardSkeleton key={i} />)
        : data?.items.map((item) => <PersonCard key={String(item.uid)} item={item} />)}

      {data && data.items.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <UserPlus className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">暂无粉丝数据</p>
        </div>
      )}

      {data && (
        <Pagination
          page={page}
          hasMore={data.page.has_more}
          onPrev={() => setPage((p) => Math.max(0, p - 1))}
          onNext={() => setPage((p) => p + 1)}
        />
      )}
    </div>
  )
}

function FolloweesTab() {
  const [page, setPage] = useState(0)
  const perPage = 20
  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['followees', page],
    queryFn: () => api.social.followees(page, perPage),
    staleTime: 5 * 60_000,
  })

  const totalText =
    typeof data?.page.total === 'number'
      ? `共 ${data.page.total} 人`
      : `本页 ${data?.items.length ?? 0} 人`

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm text-slate-400">{data ? totalText : '加载中...'}</p>
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-500 hover:text-slate-700"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {isLoading
        ? Array.from({ length: 5 }).map((_, i) => <PersonCardSkeleton key={i} />)
        : data?.items.map((item) => <PersonCard key={String(item.uid)} item={item} />)}

      {data && data.items.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">暂无关注的用户</p>
        </div>
      )}

      {data && (
        <Pagination
          page={page}
          hasMore={data.page.has_more}
          onPrev={() => setPage((p) => Math.max(0, p - 1))}
          onNext={() => setPage((p) => p + 1)}
        />
      )}
    </div>
  )
}

function MomentsTab() {
  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['moments'],
    queryFn: () => api.social.moments(),
    staleTime: 3 * 60_000,
  })

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm text-slate-400">
          {data ? `${data.total} 条动态` : '加载中...'}
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-500 hover:text-slate-700"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {isLoading
        ? Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-4 border border-slate-100">
              <div className="flex items-start gap-3">
                <Skeleton className="h-9 w-9 rounded-full flex-shrink-0" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-48 mb-2" />
                  <Skeleton className="h-16 w-full rounded-xl" />
                </div>
              </div>
            </div>
          ))
        : data?.items.map((item, i) => (
            <MomentCard key={`${item.action_time}-${i}`} item={item} />
          ))}

      {data && data.items.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <Activity className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">暂无关注动态</p>
        </div>
      )}
    </div>
  )
}

export function SocialPage() {
  const [activeTab, setActiveTab] = useState<TabId>('followers')

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          读者洞察
          <span className="px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-600 text-xs font-bold border border-violet-500/20 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            数据追踪
          </span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">粉丝列表、关注列表与关注动态的综合视图</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap flex items-center gap-1.5 transition-all ${
              activeTab === id
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:border-violet-300 hover:text-violet-600'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'followers' && <FollowersTab />}
      {activeTab === 'followees' && <FolloweesTab />}
      {activeTab === 'moments' && <MomentsTab />}
    </div>
  )
}
