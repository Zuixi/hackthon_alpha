import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'

export function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code') || searchParams.get('authorization_code')
    if (!code) {
      setError('No authorization code received')
      return
    }

    const redirectUri = `${window.location.origin}/auth/callback`

    api.auth.callback(code, redirectUri)
      .then(({ access_token }) => {
        localStorage.setItem('token', access_token)
        navigate('/hot', { replace: true })
      })
      .catch((err) => {
        setError(err.message || 'Login failed')
      })
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-destructive">{error}</p>
          <a href="/login" className="text-primary underline">返回登录</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex items-center gap-3">
        <div className="animate-spin h-6 w-6 rounded-full border-4 border-primary border-t-transparent" />
        <span className="text-muted-foreground">正在登录...</span>
      </div>
    </div>
  )
}
