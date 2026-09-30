import type { BookingStatus, PaymentStatus, UserRole } from '@/lib/types'
import { BOOKING_STATUS_LABEL, PAYMENT_STATUS_LABEL, ROLE_LABEL } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

/**
 * Status chips use a tinted dot rather than a filled background: with three
 * states to distinguish at a glance across dense tables, colour alone on a
 * filled pill reads as noise, while a dot plus muted text stays quiet.
 */
function Dot({ className }: { className: string }) {
  return <span className={cn('size-1.5 shrink-0 rounded-full', className)} aria-hidden="true" />
}

const BOOKING_TONE: Record<BookingStatus, string> = {
  pending: 'bg-warning',
  confirmed: 'bg-success',
  cancelled: 'bg-muted-foreground/50',
  completed: 'bg-primary/60',
}

export function BookingStatusBadge({ status, className }: { status: BookingStatus; className?: string }) {
  return (
    <Badge variant="outline" className={cn('gap-1.5 font-normal', className)}>
      <Dot className={BOOKING_TONE[status]} />
      {BOOKING_STATUS_LABEL[status]}
    </Badge>
  )
}

const PAYMENT_TONE: Record<PaymentStatus, string> = {
  unpaid: 'bg-warning',
  paid_on_site: 'bg-success',
  refunded: 'bg-muted-foreground/50',
}

export function PaymentStatusBadge({
  status,
  className,
}: {
  status: PaymentStatus
  className?: string
}) {
  return (
    <Badge variant="outline" className={cn('gap-1.5 font-normal', className)}>
      <Dot className={PAYMENT_TONE[status]} />
      {PAYMENT_STATUS_LABEL[status]}
    </Badge>
  )
}

const ROLE_TONE: Record<UserRole, string> = {
  admin: 'bg-primary',
  owner: 'bg-warning',
  customer: 'bg-muted-foreground/50',
}

export function RoleBadge({ role, className }: { role: UserRole; className?: string }) {
  return (
    <Badge variant="outline" className={cn('gap-1.5 font-normal', className)}>
      <Dot className={ROLE_TONE[role]} />
      {ROLE_LABEL[role]}
    </Badge>
  )
}
