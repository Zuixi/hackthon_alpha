const API_BASE = import.meta.env.VITE_API_URL || ''

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Request failed')
  }

  return res.json()
}

export const api = {
  auth: {
    getLoginUrl: (redirectUri?: string) =>
      request<{ url: string }>(`/api/auth/login-url${redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''}`),
    callback: (code: string, redirectUri?: string) =>
      request<{ access_token: string }>('/api/auth/callback', {
        method: 'POST',
        body: JSON.stringify({ code, redirect_uri: redirectUri }),
      }),
    me: () => request<import('@/types/api').User>('/api/auth/me'),
  },

  hot: {
    list: (limit = 50) =>
      request<import('@/types/api').HotTopicListResponse>(`/api/hot?limit=${limit}`),
    get: (id: string) =>
      request<import('@/types/api').HotTopic>(`/api/hot/${id}`),
  },

  chat: {
    listSessions: () =>
      request<import('@/types/api').ChatSession[]>('/api/chat'),
    createSession: (hotTopicId?: string, title?: string) =>
      request<import('@/types/api').ChatSessionDetail>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ hot_topic_id: hotTopicId, title }),
      }),
    getSession: (id: string) =>
      request<import('@/types/api').ChatSessionDetail>(`/api/chat/${id}`),
    deleteSession: (id: string) =>
      request<{ ok: boolean }>(`/api/chat/${id}`, { method: 'DELETE' }),
    sendMessage: (sessionId: string, message: string) => {
      const token = getToken()
      return fetch(`${API_BASE}/api/chat/${sessionId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message }),
      })
    },
  },

  cards: {
    list: (params?: { tag?: string; search?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams()
      if (params?.tag) qs.set('tag', params.tag)
      if (params?.search) qs.set('search', params.search)
      if (params?.limit) qs.set('limit', String(params.limit))
      if (params?.offset) qs.set('offset', String(params.offset))
      return request<import('@/types/api').CardListResponse>(`/api/cards?${qs}`)
    },
    create: (data: { content: string; tags?: string[]; hot_topic_id?: string; chat_session_id?: string }) =>
      request<import('@/types/api').IdeaCard>('/api/cards', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) =>
      request<import('@/types/api').IdeaCard>(`/api/cards/${id}`),
    update: (id: string, data: { content?: string; tags?: string[] }) =>
      request<import('@/types/api').IdeaCard>(`/api/cards/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<{ ok: boolean }>(`/api/cards/${id}`, { method: 'DELETE' }),
    tags: () => request<string[]>('/api/cards/tags'),
  },

  publish: {
    toZhihu: (content: string) =>
      request<{ success: boolean; message: string; url: string }>('/api/publish', {
        method: 'POST',
        body: JSON.stringify({ content }),
      }),
  },

  social: {
    followees: (page = 0, perPage = 20) =>
      request<import('@/types/api').FolloweeListResponse>(
        `/api/social/followees?page=${page}&per_page=${perPage}`,
      ),
    moments: () =>
      request<import('@/types/api').MomentListResponse>('/api/social/moments'),
  },
}
