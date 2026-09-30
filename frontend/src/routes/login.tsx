import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { AuthLayout, AuthLink } from '@/components/auth-layout'
import { PasswordInput } from '@/components/password-input'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/lib/auth-context'
import { useMutation } from '@/hooks/use-async'
import { LogIn } from '@/components/animate-ui/icons/log-in'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const { run, isPending, error } = useMutation(async () => login({ email, password }))

  // Send people back to whatever they were trying to reach before the guard
  // bounced them here.
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const user = await run()
    if (!user) return
    toast.success(`Welcome back, ${user.full_name.split(' ')[0]}`)
    navigate(from, { replace: true })
  }

  return (
    <AuthLayout
      title="Sign in"
      description="Access your bookings and, if you own pitches, your schedule."
      footer={
        <>
          New here? <AuthLink to="/register">Create an account</AuthLink>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <Input
              id="email"
              type="email"
              name="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </Field>

          <Field>
            <FieldLabel htmlFor="password">Password</FieldLabel>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>

          {error ? <FieldError>{error.message}</FieldError> : null}
        </FieldGroup>

        <Button type="submit" size="lg" className="w-full" disabled={isPending}>
          {isPending ? 'Signing in…' : 'Sign in'}
          {isPending ? null : <LogIn size={15} animateOnTap />}
        </Button>

        <FieldDescription className="text-center">
          Seeded demo logins: <code>customer@example.com</code> / <code>Customer@12345</code>
        </FieldDescription>
      </form>
    </AuthLayout>
  )
}
