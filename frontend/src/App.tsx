import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { Layout } from '@/components/layout'
import { LoginPage } from '@/pages/login'
import { AuthCallback } from '@/pages/auth-callback'
import { HotPage } from '@/pages/hot'
import { ChatPage } from '@/pages/chat'
import { ChatSessionPage } from '@/pages/chat-session'
import { CardsPage } from '@/pages/cards'
import { SocialPage } from '@/pages/social'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/hot" replace />} />
              <Route path="/hot" element={<HotPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:sessionId" element={<ChatSessionPage />} />
              <Route path="/cards" element={<CardsPage />} />
              <Route path="/social" element={<SocialPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
