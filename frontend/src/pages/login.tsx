import { useState, useEffect, useRef, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import { Flame, MessageSquare, Lightbulb, Globe } from 'lucide-react'
import { api } from '@/lib/api'

const TYPING_TEXT = '聚合全网热点，AI 辅助创作，3 分钟找到切入角度'

const MARQUEE_ITEMS = [
  '🔥 OpenAI 发布 GPT-5 引发全网讨论',
  '💡 短视频选题：职场反内卷的5个新角度',
  '📊 小米汽车周销量破纪录',
  '🤖 AI 分析：新能源车企竞争格局',
  '🔥 知乎热榜：如何看待延迟退休新政',
  '💡 灵感卡片："35岁危机"内容结构建议',
  '📊 B站热门：某游戏实机演示播放量破千万',
  '🤖 AI 建议：从3个心理学角度切入',
]

function useTypingEffect(text: string, delay = 800) {
  const [displayed, setDisplayed] = useState('')

  useEffect(() => {
    let idx = 0
    const timer = setTimeout(function tick() {
      if (idx < text.length) {
        setDisplayed(text.slice(0, idx + 1))
        idx++
        setTimeout(tick, 50 + Math.random() * 50)
      }
    }, delay)
    return () => clearTimeout(timer)
  }, [text, delay])

  return displayed
}

function useMouseGlow() {
  const glowRef = useRef<HTMLDivElement>(null)

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (glowRef.current) {
      glowRef.current.style.left = `${e.clientX}px`
      glowRef.current.style.top = `${e.clientY}px`
    }
  }, [])

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove)
    return () => document.removeEventListener('mousemove', handleMouseMove)
  }, [handleMouseMove])

  return glowRef
}

function BackgroundOrbs() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      <div className="login-orb login-orb-amber" />
      <div className="login-orb login-orb-violet" />
      <div className="login-orb login-orb-cyan" />
    </div>
  )
}

function Marquee() {
  const content = MARQUEE_ITEMS.join('\u00A0\u00A0\u00A0')
  const doubled = `${content}\u00A0\u00A0\u00A0${content}`

  return (
    <div className="absolute top-0 left-0 right-0 h-10 bg-gradient-to-r from-amber-500/10 via-violet-500/10 to-cyan-500/10 border-b border-white/40 z-20 flex items-center">
      <div className="w-full overflow-hidden whitespace-nowrap text-xs text-slate-500 font-medium">
        <div className="login-marquee-content">{doubled}</div>
      </div>
    </div>
  )
}

function FeatureCardHot() {
  return (
    <div className="login-glass-feature absolute top-[15%] left-[8%] md:left-[12%] w-60 rounded-2xl p-5 rotate-[-6deg] login-animate-fly-left hidden md:block">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
          <Flame className="w-5 h-5 text-amber-500" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-800">热点发现</p>
          <p className="text-[11px] text-slate-500 mt-0.5">全网实时热榜，精准发现创作切入点</p>
        </div>
      </div>
    </div>
  )
}

function FeatureCardChat() {
  return (
    <div className="login-glass-feature absolute top-[20%] right-[8%] md:right-[10%] w-60 rounded-2xl p-5 rotate-[4deg] login-animate-fly-right hidden md:block">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-500/15 flex items-center justify-center flex-shrink-0">
          <MessageSquare className="w-5 h-5 text-violet-500" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-800">智能对话</p>
          <p className="text-[11px] text-slate-500 mt-0.5">AI 深度分析，轻松找到写作角度</p>
        </div>
      </div>
    </div>
  )
}

function FeatureCardIdea() {
  return (
    <div className="login-glass-feature absolute bottom-[18%] left-[10%] md:left-[15%] w-60 rounded-2xl p-5 rotate-[3deg] login-animate-fly-bottom-left hidden md:block">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-cyan-500/15 flex items-center justify-center flex-shrink-0">
          <Lightbulb className="w-5 h-5 text-cyan-500" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-800">灵感沉淀</p>
          <p className="text-[11px] text-slate-500 mt-0.5">随手捕捉灵感，素材随时取用</p>
        </div>
      </div>
    </div>
  )
}

function SocialProof() {
  const seeds = [1, 2, 3, 4, 5]
  return (
    <div className="flex items-center justify-center gap-3 pt-6 border-t border-slate-200/60">
      <div className="login-avatar-group flex items-center">
        {seeds.map((seed) => (
          <img
            key={seed}
            src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`}
            alt="user"
            loading="lazy"
          />
        ))}
      </div>
      <div className="text-left">
        <p className="text-xs text-slate-900 font-bold">2,400+</p>
        <p className="text-[10px] text-slate-400">创作者正在捕捉热点</p>
      </div>
    </div>
  )
}

export function LoginPage() {
  const [loading, setLoading] = useState(false)
  const token = localStorage.getItem('token')
  const typedText = useTypingEffect(TYPING_TEXT)
  const glowRef = useMouseGlow()

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
    <div className="h-screen w-screen relative overflow-hidden login-page-bg">
      {/* Cursor glow */}
      <div ref={glowRef} className="login-cursor-glow" />

      {/* Background color orbs */}
      <BackgroundOrbs />

      {/* Top marquee */}
      <Marquee />

      {/* Feature cards (desktop only) */}
      <FeatureCardHot />
      <FeatureCardChat />
      <FeatureCardIdea />

      {/* Central card */}
      <div className="relative z-10 h-full flex items-center justify-center px-4">
        <div className="login-glass-card rounded-3xl p-8 md:p-12 w-full max-w-lg text-center login-animate-fly-in">
          {/* Logo */}
          <div className="mb-6 flex flex-col items-center gap-2">
            <div className="relative inline-block">
              <img
                src="/icon.jpeg"
                alt="AlphaBot"
                className="w-16 h-16 rounded-2xl shadow-lg shadow-slate-900/20 object-cover"
              />
              <div
                className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full border-2 border-white"
                style={{ animation: 'login-pulse-slow 4s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}
              />
            </div>
            <span style={{ fontSize: '18px', fontWeight: 600, color: '#64748b' }}>AlphaBot</span>
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3 tracking-tight">
            捕捉每一个<span className="login-title-line">爆款可能</span>
          </h1>

          {/* Typing subtitle */}
          <p className="text-slate-500 text-base md:text-lg mb-8 h-6">
            <span className="login-typing-cursor">{typedText}</span>
          </p>

          {/* Feature pills */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 text-xs font-semibold border border-amber-500/20">
              热点发现
            </span>
            <span className="px-3 py-1 rounded-full bg-violet-500/10 text-violet-500 text-xs font-semibold border border-violet-500/20">
              AI 辅助
            </span>
            <span className="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-500 text-xs font-semibold border border-cyan-500/20">
              灵感沉淀
            </span>
          </div>

          {/* Login button */}
          <div className="mb-8">
            <button
              className="login-btn-primary w-full py-3.5 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2"
              onClick={handleLogin}
              disabled={loading}
            >
              <Globe className="w-5 h-5" />
              {loading ? '跳转中...' : '使用知乎账号登录'}
            </button>
          </div>

          {/* Social proof */}
          <SocialProof />
        </div>
      </div>
    </div>
  )
}
