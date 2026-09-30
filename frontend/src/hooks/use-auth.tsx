import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { onTokenChange, refreshSession, setAccessToken } from '@/lib/api'
import { authApi } from '@/lib/endpoints'
import { AuthContext, type AuthContextValue, type AuthStatus } from '@/lib/auth-context'
import type { LoginPayload, RegisterPayload } from '@/lib/types'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthContextValue['user']>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  // On first paint the access token is gone (it only ever lived in memory), so
  // the session is re-established from the httpOnly refresh cookie. Until that
  // settles we must not render protected routes or bounce the user to /login.
  useEffect(() => {
    let cancelled = false

    void (async () => {
      const session = await refreshSession()
      if (cancelled) return
      setUser(session?.user ?? null)
      setStatus(session ? 'authenticated' : 'anonymous')
    })()

    return () => {
      cancelled = true
    }
  }, [])

  // A refresh can also be triggered by the API client on a 401; keep the
  // provider in step with it rather than only with its own login/logout calls.
  useEffect(
    () =>
      onTokenChange((token) => {
        if (token === null) {
          setUser(null)
          setStatus('anonymous')
        }
      }),
    [],
  )

  const login = useCallback(async (payload: LoginPayload) => {
    const session = await authApi.login(payload)
    setAccessToken(session.access_token)
    setUser(session.user)
    setStatus('authenticated')
    return session.user
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const session = await authApi.register(payload)
    setAccessToken(session.access_token)
    setUser(session.user)
    setStatus('authenticated')
    return session.user
  }, [])

  const clearLocalSession = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    setStatus('anonymous')
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      // Clear locally even if the call failed, otherwise a dead session lingers
      // in the UI until the next refresh attempt.
      clearLocalSession()
    }
  }, [clearLocalSession])

  const logoutAll = useCallback(async () => {
    try {
      await authApi.logoutAll()
    } finally {
      clearLocalSession()
    }
  }, [clearLocalSession])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isAdmin: user?.role === 'admin',
      isOwner: user?.role === 'owner' || user?.role === 'admin',
      login,
      register,
      logout,
      logoutAll,
    }),
    [user, status, login, register, logout, logoutAll],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
