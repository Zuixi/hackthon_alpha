import { useState, useEffect, useRef, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import { Flame, MessageSquare, Lightbulb, Zap, Globe } from 'lucide-react'
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

const SCATTERED_CARDS = [
  { text: '知乎热榜 #1', sub: '如何看待...', color: 'hot' },
  { text: '微博热搜', sub: '爆', color: 'hot' },
  { text: 'AI 建议', sub: '从技术角度切入...', color: 'ai' },
  { text: '灵感碎片', sub: '记录于 2分钟前', color: 'idea' },
  { text: 'B站热门', sub: '播放量 520万', color: 'hot' },
  { text: '抖音热榜', sub: '挑战话题', color: 'hot' },
  { text: '对话记录', sub: 'GPT-5 分析', color: 'ai' },
  { text: '选题库', sub: '待完善', color: 'idea' },
  { text: '数据周报', sub: '阅读量趋势', color: 'idea' },
  { text: '热点追踪', sub: '自动更新中...', color: 'hot' },
  { text: 'AI 大纲', sub: '已生成', color: 'ai' },
  { text: '素材库', sub: '12 个标签', color: 'idea' },
] as const

const COLOR_MAP = {
  hot: { bg: 'bg-amber-500/5 border-amber-500/20', text: 'text-amber-500' },
  ai: { bg: 'bg-violet-500/5 border-violet-500/20', text: 'text-violet-500' },
  idea: { bg: 'bg-cyan-500/5 border-cyan-500/20', text: 'text-cyan-500' },
} as const

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

function ScatteredCards() {
  const cards = useRef(
    SCATTERED_CARDS.map(() => ({
      x: Math.random() * 90 + 5,
      y: Math.random() * 85 + 5,
      rot: Math.random() * 30 - 15,
      scale: 0.7 + Math.random() * 0.3,
      delay: Math.random() * 2,
    })),
  )

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {SCATTERED_CARDS.map((card, i) => {
        const pos = cards.current[i]
        const colors = COLOR_MAP[card.color]
        return (
          <div
            key={i}
            className={`absolute login-bg-card rounded-lg p-2 border ${colors.bg} login-animate-fly-in`}
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              transform: `scale(${pos.scale}) rotate(${pos.rot}deg)`,
              animationDelay: `${pos.delay}s`,
              zIndex: 1,
            }}
          >
            <p className={`text-[10px] font-bold ${colors.text} mb-0.5`}>{card.text}</p>
            <p className="text-[8px] text-slate-400">{card.sub}</p>
          </div>
        )
      })}
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
    <div className="login-glass-feature absolute top-[15%] left-[8%] md:left-[12%] w-64 rounded-2xl p-5 rotate-[-6deg] login-animate-fly-left hidden md:block">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
          <Flame className="w-4 h-4 text-amber-500" />
        </div>
        <span className="text-xs font-bold text-slate-700">热点发现</span>
        <span className="ml-auto w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
      </div>
      <div className="space-y-2">
        {[
          { rank: 1, title: 'OpenAI 发布 GPT-5', heat: '2.4M 热' },
          { rank: 2, title: '小米汽车销量破纪录', heat: '1.8M 热' },
          { rank: 3, title: '延迟退休新政解读', heat: '1.2M 热' },
        ].map((item) => (
          <div key={item.rank} className="flex items-center gap-2 text-xs text-slate-600">
            <span className="text-amber-500 font-bold">{item.rank}</span>
            <span className="truncate">{item.title}</span>
            <span className="ml-auto text-[10px] text-slate-400">{item.heat}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-slate-200/50 flex items-center justify-between">
        <span className="text-[10px] text-slate-400">tophub.today</span>
        <span className="text-[10px] text-amber-500 font-medium">刚刚更新</span>
      </div>
    </div>
  )
}

function FeatureCardChat() {
  return (
    <div className="login-glass-feature absolute top-[20%] right-[8%] md:right-[10%] w-72 rounded-2xl p-5 rotate-[4deg] login-animate-fly-right hidden md:block">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
          <MessageSquare className="w-4 h-4 text-violet-500" />
        </div>
        <span className="text-xs font-bold text-slate-700">智能对话</span>
        <span className="ml-auto px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-500 text-[10px] font-bold">AI</span>
      </div>
      <div className="space-y-3">
        <div className="flex gap-2">
          <div className="w-6 h-6 rounded-full bg-slate-200 flex-shrink-0" />
          <div className="bg-slate-100 rounded-lg rounded-tl-none p-2 text-[11px] text-slate-600 max-w-[85%]">
            帮我分析"GPT-5发布"这个热点，适合从哪些角度切入？
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <div className="bg-violet-500/10 rounded-lg rounded-tr-none p-2 text-[11px] text-slate-700 max-w-[90%] border border-violet-500/10">
            <span className="text-violet-500 font-semibold">1. 技术突破角度</span>
            <br />
            <span className="text-slate-500">对比 GPT-4，分析多模态能力的实际提升...</span>
            <div className="mt-1 flex gap-1">
              <span className="text-[9px] px-1 py-0.5 bg-white rounded text-violet-500">生成卡片</span>
              <span className="text-[9px] px-1 py-0.5 bg-white rounded text-slate-400">重新生成</span>
            </div>
          </div>
          <div className="w-6 h-6 rounded-full bg-violet-500/20 flex-shrink-0 flex items-center justify-center">
            <Zap className="w-3 h-3 text-violet-500" />
          </div>
        </div>
      </div>
    </div>
  )
}

function FeatureCardIdea() {
  return (
    <div className="login-glass-feature absolute bottom-[18%] left-[10%] md:left-[15%] w-60 rounded-2xl p-5 rotate-[3deg] login-animate-fly-bottom-left hidden md:block">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
          <Lightbulb className="w-4 h-4 text-cyan-500" />
        </div>
        <span className="text-xs font-bold text-slate-700">灵感沉淀</span>
      </div>
      <div className="bg-white/60 rounded-xl p-3 mb-2 border border-white/60">
        <p className="text-xs text-slate-700 font-medium mb-1">职场反内卷选题</p>
        <p className="text-[10px] text-slate-500 line-clamp-2">
          从心理学"习得性无助"角度分析，给出3个 actionable 的建议...
        </p>
        <div className="flex gap-1 mt-2">
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-500">职场</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-500">心理学</span>
        </div>
      </div>
      <div className="bg-white/60 rounded-xl p-3 border border-white/60">
        <p className="text-xs text-slate-700 font-medium mb-1">新能源车企对比</p>
        <p className="text-[10px] text-slate-500 line-clamp-2">
          数据表格：小米、特斯拉、比亚迪 Q1 销量与口碑对比...
        </p>
        <div className="flex gap-1 mt-2">
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-500">数据分析</span>
        </div>
      </div>
    </div>
  )
}

function FeatureCardStats() {
  return (
    <div className="login-glass-feature absolute bottom-[25%] right-[12%] md:right-[15%] px-4 py-3 rounded-xl rotate-[-2deg] login-animate-fly-bottom-right hidden md:flex items-center gap-3">
      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-lg">
        📈
      </div>
      <div>
        <p className="text-xs font-bold text-slate-800">数据洞察</p>
        <p className="text-[10px] text-slate-500">本周阅读量 +128%</p>
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
    <div className="h-screen w-screen relative overflow-hidden bg-gradient-to-br from-slate-50 via-slate-100/50 to-white">
      {/* Cursor glow */}
      <div ref={glowRef} className="login-cursor-glow" />

      {/* Background scattered cards */}
      <ScatteredCards />

      {/* Top marquee */}
      <Marquee />

      {/* Feature cards (desktop only) */}
      <FeatureCardHot />
      <FeatureCardChat />
      <FeatureCardIdea />
      <FeatureCardStats />

      {/* Central card */}
      <div className="relative z-10 h-full flex items-center justify-center px-4">
        <div className="login-glass-card rounded-3xl p-8 md:p-12 w-full max-w-lg text-center login-animate-fly-in">
          {/* Logo */}
          <div className="mb-6 relative inline-block">
            <div className="w-16 h-16 bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-slate-900/20">
              <Flame className="w-8 h-8 text-white" />
            </div>
            <div
              className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full border-2 border-white"
              style={{ animation: 'login-pulse-slow 4s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}
            />
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
