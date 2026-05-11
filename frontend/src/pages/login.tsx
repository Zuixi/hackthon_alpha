import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Flame, MessageSquare, Lightbulb } from 'lucide-react'
import { api } from '@/lib/api'

export function LoginPage() {
  const [loading, setLoading] = useState(false)
  const token = localStorage.getItem('token')

  if (token) return <Navigate to="/hot" replace />

  const handleLogin = async () => {
    setLoading(true)
    try {
      const redirectUri = `${window.location.origin}/auth/callback`
      const { url } = await api.auth.getLoginUrl(redirectUri)
      window.location.href = url
    } catch {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-2">
            <Flame className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">知乎创作助手</CardTitle>
          <CardDescription>AI 驱动的一站式内容创作平台</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              { icon: Flame, label: '热点发现' },
              { icon: MessageSquare, label: '智能对话' },
              { icon: Lightbulb, label: '灵感沉淀' },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="p-3 rounded-lg bg-muted/50">
                <Icon className="h-5 w-5 mx-auto text-muted-foreground mb-1" />
                <span className="text-xs text-muted-foreground">{label}</span>
              </div>
            ))}
          </div>

          <Button className="w-full h-11" onClick={handleLogin} disabled={loading}>
            {loading ? '跳转中...' : '使用知乎账号登录'}
          </Button>

          <p className="text-xs text-center text-muted-foreground">
            登录即表示同意我们的服务条款
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
