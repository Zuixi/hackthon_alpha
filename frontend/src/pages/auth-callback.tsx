import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'

function extractOAuthCode(searchParams: URLSearchParams): string {
  const candidates = ['code', 'authorization_code', 'auth_code']

  for (const key of candidates) {
    const value = searchParams.get(key)
    if (value) return value
  }

  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash
  if (!hash) return ''

  const hashParams = new URLSearchParams(hash)
  for (const key of candidates) {
    const value = hashParams.get(key)
    if (value) return value
  }

  return ''
}

export function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = extractOAuthCode(searchParams)
    if (!code) {
      const providerError =
        searchParams.get('error_description') ||
        searchParams.get('error') ||
        searchParams.get('errmsg')
      setError(
        providerError
          ? `OAuth provider error: ${providerError}`
          : `No authorization code received. URL: ${window.location.pathname}${window.location.search}${window.location.hash}`,
      )
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
