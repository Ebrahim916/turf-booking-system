import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { AppShell } from '@/components/app-shell'
import { OrbScreen } from '@/components/orb-loader'
import { useAuth } from '@/lib/auth-context'
import type { UserRole } from '@/lib/types'

// Route-level splitting keeps the admin and owner surfaces out of the initial
// bundle; a customer never downloads the user-administration screen.
const ExplorePage = lazy(() =>
  import('@/routes/explore').then((m) => ({ default: m.ExplorePage })),
)
const LoginPage = lazy(() => import('@/routes/login').then((m) => ({ default: m.LoginPage })))
const RegisterPage = lazy(() =>
  import('@/routes/register').then((m) => ({ default: m.RegisterPage })),
)
const TurfDetailPage = lazy(() =>
  import('@/routes/turf-detail').then((m) => ({ default: m.TurfDetailPage })),
)
const BookingsPage = lazy(() =>
  import('@/routes/bookings').then((m) => ({ default: m.BookingsPage })),
)
const SettingsPage = lazy(() =>
  import('@/routes/settings').then((m) => ({ default: m.SettingsPage })),
)
const ManageTurfsPage = lazy(() =>
  import('@/routes/manage/turfs-list').then((m) => ({ default: m.ManageTurfsPage })),
)
const TurfEditorPage = lazy(() =>
  import('@/routes/manage/turf-editor').then((m) => ({ default: m.TurfEditorPage })),
)
const AdminUsersPage = lazy(() =>
  import('@/routes/admin/users').then((m) => ({ default: m.AdminUsersPage })),
)
const NotFoundPage = lazy(() =>
  import('@/routes/not-found').then((m) => ({ default: m.NotFoundPage })),
)

/**
 * Guards wait for the session to resolve before deciding. Redirecting while
 * `status === 'loading'` would bounce a signed-in user to /login on every hard
 * refresh, because the access token only ever lived in memory.
 */
function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user, status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <OrbScreen state="connecting" label="Restoring your session" />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />

  return children
}

function RedirectIfSignedIn({ children }: { children: ReactNode }) {
  const { user, status } = useAuth()
  if (status === 'loading') return <OrbScreen state="connecting" label="Restoring your session" />
  if (user) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Suspense fallback={<OrbScreen state="connecting" label="Loading" />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<ExplorePage />} />
          <Route path="turfs/:turfId" element={<TurfDetailPage />} />

          <Route
            path="login"
            element={
              <RedirectIfSignedIn>
                <LoginPage />
              </RedirectIfSignedIn>
            }
          />
          <Route
            path="register"
            element={
              <RedirectIfSignedIn>
                <RegisterPage />
              </RedirectIfSignedIn>
            }
          />

          <Route
            path="bookings"
            element={
              <RequireRole roles={['admin', 'owner', 'customer']}>
                <BookingsPage />
              </RequireRole>
            }
          />
          <Route
            path="settings"
            element={
              <RequireRole roles={['admin', 'owner', 'customer']}>
                <SettingsPage />
              </RequireRole>
            }
          />

          <Route
            path="manage/turfs"
            element={
              <RequireRole roles={['admin', 'owner']}>
                <ManageTurfsPage />
              </RequireRole>
            }
          />
          <Route
            path="manage/turfs/new"
            element={
              <RequireRole roles={['admin', 'owner']}>
                <TurfEditorPage />
              </RequireRole>
            }
          />
          <Route
            path="manage/turfs/:turfId"
            element={
              <RequireRole roles={['admin', 'owner']}>
                <TurfEditorPage />
              </RequireRole>
            }
          />

          <Route
            path="admin/users"
            element={
              <RequireRole roles={['admin']}>
                <AdminUsersPage />
              </RequireRole>
            }
          />

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
