import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { AuthLayout, AuthLink } from '@/components/auth-layout'
import { PasswordInput } from '@/components/password-input'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Hint } from '@/components/feedback'
import { useAuth } from '@/lib/auth-context'
import { useMutation } from '@/hooks/use-async'
import { cn } from '@/lib/utils'
import { Send } from '@/components/animate-ui/icons/send'

/**
 * Mirrors `PASSWORD_PATTERN` in `backend/app/schemas/user.py`. Duplicating it
 * here is worth it: the policy is a fixed format, and catching a weak password
 * client-side is instant. The server remains the authority.
 */
const PASSWORD_RULES = [
  { label: '8+ characters', test: (value: string) => value.length >= 8 },
  { label: 'a lowercase letter', test: (value: string) => /[a-z]/.test(value) },
  { label: 'an uppercase letter', test: (value: string) => /[A-Z]/.test(value) },
  { label: 'a digit', test: (value: string) => /\d/.test(value) },
  { label: 'a symbol', test: (value: string) => /[^\w\s]/.test(value) },
]

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')

  const unmet = useMemo(
    () => PASSWORD_RULES.filter((rule) => !rule.test(password)),
    [password],
  )

  const { run, isPending, error } = useMutation(async () =>
    register({
      email,
      password,
      full_name: fullName,
      phone: phone.trim() || null,
    }),
  )

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (unmet.length > 0) return

    const user = await run()
    if (!user) return
    toast.success('Account created')
    navigate('/', { replace: true })
  }

  return (
    <AuthLayout
      title="Create an account"
      description="Sign up as a customer to book and manage your pitches."
      footer={
        <>
          Already registered? <AuthLink to="/login">Sign in</AuthLink>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="full_name">Full name</FieldLabel>
            <Input
              id="full_name"
              name="name"
              autoComplete="name"
              required
              minLength={2}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </Field>

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
            />
          </Field>

          <Field>
            <FieldLabel htmlFor="phone">Phone</FieldLabel>
            <Input
              id="phone"
              type="tel"
              name="phone"
              autoComplete="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="Optional, 7–15 digits"
            />
            <FieldDescription>Include the country code if you use one.</FieldDescription>
          </Field>

          <Field>
            <FieldLabel htmlFor="password">Password</FieldLabel>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-invalid={unmet.length > 0 && password.length > 0}
            />
            {password ? (
              <ul className="flex flex-wrap gap-x-3 gap-y-1">
                {PASSWORD_RULES.map((rule) => {
                  const ok = rule.test(password)
                  return (
                    <li
                      key={rule.label}
                      className={cn(
                        'text-xs',
                        ok ? 'text-success' : 'text-muted-foreground',
                      )}
                    >
                      {rule.label}
                    </li>
                  )
                })}
              </ul>
            ) : (
              <Hint>
                Owner and admin accounts are provisioned by an administrator, not by public signup.
              </Hint>
            )}
          </Field>

          {error ? <FieldError>{error.message}</FieldError> : null}
        </FieldGroup>

        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={isPending || unmet.length > 0}
        >
          {isPending ? 'Creating account…' : 'Create account'}
          {isPending ? null : <Send size={15} animateOnTap />}
        </Button>
      </form>
    </AuthLayout>
  )
}
