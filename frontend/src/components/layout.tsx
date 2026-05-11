import { useState } from 'react'
import { Outlet, NavLink, Navigate } from 'react-router-dom'
import { Flame, MessageSquare, Lightbulb, LogOut, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useAuth } from '@/hooks/use-auth'

const navItems = [
  { to: '/hot', icon: Flame, label: '热点广场' },
  { to: '/chat', icon: MessageSquare, label: '创作对话' },
  { to: '/cards', icon: Lightbulb, label: '灵感卡片' },
]

function SidebarContent({ user, logout, onNavClick }: {
  user: { name: string; avatar: string } | null | undefined
  logout: () => void
  onNavClick?: () => void
}) {
  return (
    <>
      <div className="p-4 border-b">
        <h1 className="text-lg font-bold text-foreground">知乎创作助手</h1>
        <p className="text-xs text-muted-foreground mt-1">AI 驱动的内容创作平台</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t">
        <div className="flex items-center gap-3 px-2">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user?.avatar} />
            <AvatarFallback>{user?.name?.[0] || '?'}</AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.name}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={logout} className="h-8 w-8">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </>
  )
}

export function Layout() {
  const { user, isLoading, isAuthenticated, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin h-8 w-8 rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-60 border-r bg-sidebar-background flex-col">
        <SidebarContent user={user} logout={logout} />
      </aside>

      {/* Mobile header + sheet */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b bg-background">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-60 p-0 flex flex-col">
              <SidebarContent user={user} logout={logout} onNavClick={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>
          <h1 className="text-base font-bold">知乎创作助手</h1>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
