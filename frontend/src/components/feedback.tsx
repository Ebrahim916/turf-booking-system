import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { OrbBare } from '@/components/orb-loader'
import { CircleX } from '@/components/animate-ui/icons/circle-x'
import { RefreshCw } from '@/components/animate-ui/icons/refresh-cw'
import { Lightbulb } from '@/components/animate-ui/icons/lightbulb'
import { cn } from '@/lib/utils'

export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string
  description?: string
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-4', className)}>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
  orbState = 'breathing',
  className,
}: {
  title: string
  description?: string
  action?: ReactNode
  orbState?: 'breathing' | 'shaping' | 'composing'
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border px-6 py-14 text-center',
        className,
      )}
    >
      <OrbBare state={orbState} className="opacity-70" />
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action ? <div className="pt-2">{action}</div> : null}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  className,
}: {
  title?: string
  message?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/25 bg-destructive/5 px-6 py-12 text-center',
        className,
      )}
      role="alert"
    >
      <CircleX size={22} className="text-destructive" />
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          <RefreshCw size={16} animateOnHover />
          Try again
        </Button>
      ) : null}
    </div>
  )
}

/** Inline hint, used for form guidance such as the password policy. */
export function Hint({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-xs text-muted-foreground">
      <Lightbulb size={14} className="mt-0.5 shrink-0" />
      <span>{children}</span>
    </p>
  )
}
