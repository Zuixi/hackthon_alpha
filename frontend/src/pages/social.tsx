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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { api } from '@/lib/api'
import type { Followee, Moment, FollowerSnapshotItem } from '@/types/api'

type TabId = 'followees' | 'followers' | 'moments'

const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
  { id: 'followees', label: '关注列表', icon: Users },
  { id: 'followers', label: '粉丝列表', icon: UserPlus },
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

function FolloweeCard({ item }: { item: Followee }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <Avatar className="h-12 w-12">
            <AvatarImage src={item.avatar_path} />
            <AvatarFallback>
              <UserCircle className="h-6 w-6 text-muted-foreground" />
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-foreground truncate">{item.fullname}</h3>
              {item.gender && (
                <Badge variant="outline" className="text-xs shrink-0">
                  {item.gender === 'male' ? '男' : item.gender === 'female' ? '女' : item.gender}
                </Badge>
              )}
            </div>
            {item.headline && (
              <p className="text-sm text-muted-foreground line-clamp-1 mt-0.5">{item.headline}</p>
            )}
            {item.description && (
              <p className="text-xs text-muted-foreground/70 line-clamp-1 mt-0.5">
                {item.description}
              </p>
            )}
          </div>
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 inline-flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:bg-muted transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function SnapshotDelta({ item }: { item: FollowerSnapshotItem }) {
  if (item.delta === null || item.delta === 0) {
    return <span className="text-xs text-muted-foreground">持平</span>
  }
  if (item.delta > 0) {
    return (
      <span className="text-xs text-green-600 inline-flex items-center gap-1">
        <TrendingUp className="h-3 w-3" />+{item.delta}
      </span>
    )
  }
  return (
    <span className="text-xs text-red-600 inline-flex items-center gap-1">
      <TrendingDown className="h-3 w-3" />
      {item.delta}
    </span>
  )
}

function MomentCard({ item }: { item: Moment }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Avatar className="h-9 w-9 mt-0.5">
            <AvatarFallback className="text-xs">{item.actor.name?.[0] || '?'}</AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-sm text-foreground">{item.actor.name}</span>
              <span className="text-sm text-muted-foreground">{item.action_text}</span>
              {item.action_time > 0 && (
                <span className="text-xs text-muted-foreground/60 flex items-center gap-0.5">
                  <Clock className="h-3 w-3" />
                  {formatTimestamp(item.action_time)}
                </span>
              )}
            </div>
            {item.target && (
              <div className="mt-2 rounded-lg bg-muted/50 p-3">
                {item.target.title && (
                  <h4 className="font-medium text-sm text-foreground mb-1">{item.target.title}</h4>
                )}
                {item.target.excerpt && (
                  <p className="text-sm text-muted-foreground line-clamp-3">{item.target.excerpt}</p>
                )}
                {item.target.author?.name && (
                  <p className="text-xs text-muted-foreground/60 mt-1.5">
                    作者: {item.target.author.name}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
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
    typeof data?.page.total === 'number' ? `共 ${data.page.total} 人` : `本页 ${data?.items.length ?? 0} 人`

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{data ? totalText : '加载中...'}</p>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {isLoading
        ? Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        : data?.items.map((item) => <FolloweeCard key={String(item.uid)} item={item} />)}

      {data && data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>暂无关注的用户</p>
        </div>
      )}

      {data && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            上一页
          </Button>
          <span className="text-sm text-muted-foreground px-2">第 {page + 1} 页</span>
          <Button
            variant="outline"
            size="sm"
            disabled={!data.page.has_more}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      )}
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
  const totalText =
    typeof data?.page.total === 'number' ? `共 ${data.page.total} 人` : `本页 ${data?.items.length ?? 0} 人`

  return (
    <div className="space-y-3">
      <Card className="bg-muted/40">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm text-muted-foreground">粉丝数日监控</p>
              <p className="text-xl font-semibold">
                {statsQuery.data?.latest_count ?? '--'}
                <span className="text-sm font-normal text-muted-foreground ml-2">人</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                刷新时间：{statsQuery.data?.next_refresh_at ?? '每天 20:00 (Asia/Shanghai)'}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                followersQuery.refetch()
                statsQuery.refetch()
              }}
              disabled={followersQuery.isFetching || statsQuery.isFetching}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 mr-1 ${
                  followersQuery.isFetching || statsQuery.isFetching ? 'animate-spin' : ''
                }`}
              />
              刷新
            </Button>
          </div>
          {statsQuery.data && statsQuery.data.items.length > 0 && (
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {statsQuery.data.items.slice(-7).map((item) => (
                <div key={item.snapshot_date} className="rounded-md border bg-background px-2.5 py-1.5 shrink-0">
                  <p className="text-xs text-muted-foreground">{item.snapshot_date}</p>
                  <p className="text-sm font-medium">{item.follower_count}</p>
                  <SnapshotDelta item={item} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{data ? totalText : '加载中...'}</p>
      </div>

      {followersQuery.isLoading
        ? Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        : data?.items.map((item) => <FolloweeCard key={String(item.uid)} item={item} />)}

      {data && data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <UserPlus className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>暂无粉丝数据</p>
        </div>
      )}

      {data && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            上一页
          </Button>
          <span className="text-sm text-muted-foreground px-2">第 {page + 1} 页</span>
          <Button
            variant="outline"
            size="sm"
            disabled={!data.page.has_more}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
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
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {data ? `${data.total} 条动态` : '加载中...'}
        </p>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {isLoading
        ? Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <Skeleton className="h-9 w-9 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-48 mb-2" />
                    <Skeleton className="h-16 w-full rounded-lg" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        : data?.items.map((item, i) => <MomentCard key={`${item.action_time}-${i}`} item={item} />)}

      {data && data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Activity className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>暂无关注动态</p>
        </div>
      )}
    </div>
  )
}

export function SocialPage() {
  const [activeTab, setActiveTab] = useState<TabId>('followees')

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Users className="h-6 w-6 text-blue-500" />
          社交圈
        </h2>
        <p className="text-sm text-muted-foreground mt-1">查看关注列表、粉丝列表与关注动态</p>
      </div>

      {/* Tabs */}
      <div className="flex rounded-lg border bg-muted p-1 mb-6 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={activeTab === id ? 'default' : 'ghost'}
            size="sm"
            className="gap-1.5"
            onClick={() => setActiveTab(id)}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'followees' && <FolloweesTab />}
      {activeTab === 'followers' && <FollowersTab />}
      {activeTab === 'moments' && <MomentsTab />}
    </div>
  )
}
