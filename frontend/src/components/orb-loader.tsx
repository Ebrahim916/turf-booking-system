import type { OrbState } from 'thinking-orbs'
import { ThinkingOrb } from 'thinking-orbs'

import { cn } from '@/lib/utils'

/**
 * Loading affordances, built on thinking-orbs.
 *
 * The orbs are strictly monochrome and auto-resolve their ink from the
 * surrounding theme, which is what keeps them at home in a minimal palette.
 * Each state maps to the verb the app is actually performing, so the animation
 * carries information rather than just filling space:
 *
 *   connecting — restoring the session from the refresh cookie
 *   searching  — fetching and filtering a list
 *   solving    — submitting a form or resolving a conflict
 *   working    — a generic write in flight
 *   breathing  — idle or waiting, e.g. a day with no slots
 */

type OrbLoaderProps = {
  state?: OrbState
  label?: string
  className?: string
  /** Hides the visible label; the `aria-label` still announces it. */
  labelHidden?: boolean
}

/** Full-viewport loader for route transitions and first paint. */
export function OrbScreen({ state = 'connecting', label = 'Loading' }: OrbLoaderProps) {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background"
      role="status"
      aria-live="polite"
    >
      <ThinkingOrb state={state} size={64} aria-label={label} />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  )
}

/** Centred loader for a section that is still fetching. */
export function OrbPanel({ state = 'working', label = 'Loading', className }: OrbLoaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border py-16',
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <ThinkingOrb state={state} size={32} aria-label={label} />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  )
}

/** Small inline orb for button labels and table cells. */
export function OrbInline({ state = 'working', label = 'Loading' }: OrbLoaderProps) {
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-live="polite">
      <ThinkingOrb state={state} size={20} aria-label={label} />
      <span className="text-sm text-muted-foreground">{label}</span>
    </span>
  )
}

/** Bare orb, no copy — for use inside an existing layout. */
export function OrbBare({ state = 'working', className }: OrbLoaderProps) {
  return <ThinkingOrb state={state} size={32} className={className} aria-hidden="true" />
}

/** Slot-grid placeholder that keeps the page from reflowing when slots load. */
export function OrbSlotGrid({ label = 'Checking availability' }: OrbLoaderProps) {
  return (
    <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4" role="status" aria-live="polite">
      <div className="col-span-full flex items-center justify-center gap-3 py-10">
        <ThinkingOrb state="searching" size={32} aria-label={label} />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}
