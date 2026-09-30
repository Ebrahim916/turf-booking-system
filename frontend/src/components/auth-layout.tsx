import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ThinkingOrb } from 'thinking-orbs'

/**
 * Shared chrome for the sign-in / sign-up screens: a single centred column with
 * the brand mark, so both flows feel like one surface rather than two.
 */
export function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string
  description: string
  children: ReactNode
  footer: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-[70dvh] w-full max-w-sm flex-col justify-center py-8">
      <div className="flex flex-col items-center gap-3 text-center">
        <ThinkingOrb state="composing" size={32} aria-hidden="true" />
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      <div className="mt-8">{children}</div>

      <p className="mt-6 text-center text-sm text-muted-foreground">{footer}</p>
    </div>
  )
}

export function AuthLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className="font-medium text-foreground underline underline-offset-4">
      {children}
    </Link>
  )
}
