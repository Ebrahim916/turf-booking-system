import type { ElementType } from 'react'
import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { ThinkingOrb } from 'thinking-orbs'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { RoleBadge } from '@/components/status-badge'
import { ThemeToggle } from '@/components/theme-toggle'
import { useAuth } from '@/lib/auth-context'
import { cn } from '@/lib/utils'
import { LogIn } from '@/components/animate-ui/icons/log-in'
import { LogOut } from '@/components/animate-ui/icons/log-out'
import { User } from '@/components/animate-ui/icons/user'
import { Key } from '@/components/animate-ui/icons/key'
import { LayoutDashboard } from '@/components/animate-ui/icons/layout-dashboard'
import { Kanban } from '@/components/animate-ui/icons/kanban'
import { Users } from '@/components/animate-ui/icons/users'
import { Compass } from '@/components/animate-ui/icons/compass'
import { Ellipsis } from '@/components/animate-ui/icons/ellipsis'

type NavItem = {
  to: string
  label: string
  // Each registry icon declares its own animation-name union in its props, so
  // they are not mutually assignable to a concrete component type. `ElementType`
  // is the honest widening; the nav only ever passes `size`.
  icon: ElementType
  end?: boolean
}

/**
 * Navigation is derived from the role rather than filtered per-render, so a
 * user never sees a link they would only be refused by the server. The server
 * still enforces this — these are affordances, not permissions.
 */
function useNavItems(): NavItem[] {
  const { user, isOwner, isAdmin } = useAuth()

  const items: NavItem[] = [{ to: '/', label: 'Explore', icon: Compass, end: true }]

  if (user) {
    items.push({ to: '/bookings', label: 'Bookings', icon: Kanban })
  }
  if (isOwner) {
    items.push({ to: '/manage/turfs', label: 'My turfs', icon: LayoutDashboard })
  }
  if (isAdmin) {
    items.push({ to: '/admin/users', label: 'Users', icon: Users })
  }

  return items
}

function NavLinks({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  return (
    <>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )
          }
        >
          <item.icon size={16} />
          {item.label}
        </NavLink>
      ))}
    </>
  )
}

function UserMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null

  async function handleSignOut() {
    await logout()
    toast.success('Signed out')
    navigate('/')
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Account menu">
          <User size={16} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-1.5">
          <span className="truncate text-sm font-medium">{user.full_name}</span>
          <span className="truncate text-xs font-normal text-muted-foreground">
            {user.email}
          </span>
          <RoleBadge role={user.role} className="mt-0.5 w-fit" />
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate('/settings')}>
          <User />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/settings#password')}>
          <Key />
          Change password
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={handleSignOut}>
          <LogOut />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function AppShell() {
  const { user, isAdmin } = useAuth()
  const navItems = useNavItems()
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-2 px-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mr-2 flex items-center gap-2 rounded-md font-semibold tracking-tight"
          >
            <ThinkingOrb state="breathing" size={20} theme="auto" aria-hidden="true" />
            <span>Turf</span>
          </button>

          <nav className="hidden items-center gap-1 md:flex">
            <NavLinks items={navItems} />
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            {user ? (
              <UserMenu />
            ) : (
              <Button size="sm" onClick={() => navigate('/login')}>
                <LogIn size={15} />
                Sign in
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Toggle navigation"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
            >
              <Ellipsis size={16} />
            </Button>
          </div>
        </div>

        {mobileOpen ? (
          <nav className="flex flex-col gap-1 border-t border-border px-4 py-3 md:hidden">
            <NavLinks items={navItems} onNavigate={() => setMobileOpen(false)} />
            {!user ? (
              <Button
                className="mt-1 w-full"
                onClick={() => {
                  setMobileOpen(false)
                  navigate('/login')
                }}
              >
                <LogIn size={15} />
                Sign in
              </Button>
            ) : null}
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-border py-6">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-2 px-4 text-xs text-muted-foreground">
          <span>Turf Booking System</span>
          <span>{isAdmin ? 'Signed in as admin' : user ? 'Cash on site only' : 'Browse and book pitches'}</span>
        </div>
      </footer>
    </div>
  )
}
