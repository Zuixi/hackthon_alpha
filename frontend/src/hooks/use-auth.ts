import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useCallback } from 'react'
import { api } from '@/lib/api'
import type { User } from '@/types/api'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const token = localStorage.getItem('token')

  const { data: user, isLoading } = useQuery<User>({
    queryKey: ['user'],
    queryFn: () => api.auth.me(),
    enabled: !!token,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    queryClient.clear()
    navigate('/login')
  }, [queryClient, navigate])

  return {
    user: token ? user : null,
    isLoading: !!token && isLoading,
    isAuthenticated: !!token && !!user,
    logout,
  }
}
