export interface User {
  id: string
  zhihu_id: string
  name: string
  avatar: string
}

export interface HotTopic {
  id: string
  question_id: string | null
  title: string
  url: string
  thumbnail_url: string
  excerpt: string
  hot_score: number
  answer_count: number
  follower_count: number
  detail: string
  platform: string
  platform_name: string
  source: string
  fetch_batch: string
  fetched_at: string
}

export interface HotTopicListResponse {
  items: HotTopic[]
  total: number
}

export interface HotBatchResponse {
  fetch_batch: string
  fetched_at: string
  items: HotTopic[]
  count: number
}

export interface HotDayGroup {
  date: string
  batches: HotBatchResponse[]
  topic_count: number
}

export interface HotHistoryResponse {
  days: HotDayGroup[]
  total_days: number
}

export interface PlatformInfo {
  id: string
  name: string
  count: number
}

export interface PlatformListResponse {
  platforms: PlatformInfo[]
}

export interface KeywordGroupResponse {
  group_name: string
  display_name: string
  topics: HotTopic[]
  count: number
}

export interface GroupedHotResponse {
  groups: KeywordGroupResponse[]
  unmatched: HotTopic[]
  total: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  hot_topic_id: string | null
  hot_topic_title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatSessionDetail {
  id: string
  title: string
  hot_topic_id: string | null
  hot_topic_title: string | null
  messages: ChatMessage[]
  created_at: string
  updated_at: string
}

export interface IdeaCard {
  id: string
  title: string | null
  content: string
  tags: string[]
  hot_topic_id: string | null
  hot_topic_title: string | null
  chat_session_id: string | null
  created_at: string
  updated_at: string
}

export interface CardListResponse {
  items: IdeaCard[]
  total: number
}

// Social types
export interface Followee {
  uid: number | string
  hash_id: string
  fullname: string
  gender: string
  headline: string
  description: string
  avatar_path: string
  url: string
}

export interface MomentActor {
  name: string
}

export interface MomentTarget {
  title: string
  excerpt: string
  author: { name: string } | null
}

export interface Moment {
  actor: MomentActor
  action_text: string
  action_time: number
  target: MomentTarget | null
}

export interface FolloweeListResponse {
  items: Followee[]
  page: {
    page: number
    per_page: number
    items_count: number
    has_more: boolean
    is_end: boolean
    next_page: number | null
    total: number | null
  }
}

export interface MomentListResponse {
  items: Moment[]
  total: number
}

export interface FollowerSnapshotItem {
  snapshot_date: string
  follower_count: number
  delta: number | null
  refreshed_at: string
}

export interface FollowerStatsResponse {
  items: FollowerSnapshotItem[]
  total_days: number
  latest_count: number | null
  next_refresh_at: string
}
