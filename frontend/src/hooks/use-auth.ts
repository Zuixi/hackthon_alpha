import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useCallback } from 'react'
import { api } from '@/lib/api'
import type { User } from '@/types/api'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const bypassOAuth = import.meta.env.VITE_BYPASS_OAUTH_LOGIN === 'true'
  const token = localStorage.getItem('token')
  const shouldFetchUser = bypassOAuth || !!token

  const { data: user, isLoading } = useQuery<User>({
    queryKey: ['user'],
    queryFn: () => api.auth.me(),
    enabled: shouldFetchUser,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    queryClient.clear()
    navigate('/login')
  }, [queryClient, navigate])

  return {
    user: shouldFetchUser ? user : null,
    isLoading: shouldFetchUser && isLoading,
    isAuthenticated: bypassOAuth ? !!user : !!token && !!user,
    logout,
  }
}
