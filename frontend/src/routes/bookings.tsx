import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BookingStatusBadge, PaymentStatusBadge } from '@/components/status-badge'
import { EmptyState, ErrorState, PageHeader } from '@/components/feedback'
import { OrbPanel } from '@/components/orb-loader'
import { useAsync, useMutation } from '@/hooks/use-async'
import { useAuth } from '@/lib/auth-context'
import { bookingApi } from '@/lib/endpoints'
import {
  BOOKING_STATUS_LABEL,
  canCancelBooking,
  formatDate,
  formatMoney,
  formatTimeRange,
} from '@/lib/format'
import type { Booking, BookingStatus } from '@/lib/types'
import { Kanban } from '@/components/animate-ui/icons/kanban'
import { MapPin } from '@/components/animate-ui/icons/map-pin'
import { Clock } from '@/components/animate-ui/icons/clock'
import { X } from '@/components/animate-ui/icons/x'

const ALL = 'all'

function BookingCard({
  booking,
  canCancel,
  onCancel,
  isCancelling,
}: {
  booking: Booking
  canCancel: boolean
  onCancel: () => void
  isCancelling: boolean
}) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/turfs/${booking.turf_id}`}
              className="font-medium underline-offset-4 hover:underline"
            >
              {booking.turf_name ?? `Turf #${booking.turf_id}`}
            </Link>
            <BookingStatusBadge status={booking.status} />
            <PaymentStatusBadge status={booking.payment_status} />
          </div>

          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock size={14} />
            {formatDate(booking.start_time)} ·{' '}
            {formatTimeRange(booking.start_time, booking.end_time)}
          </p>

          {booking.notes ? (
            <p className="text-sm text-muted-foreground italic">“{booking.notes}”</p>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tabular-nums">
            {formatMoney(booking.total_price)}
          </span>

          {canCancel ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="sm" disabled={isCancelling}>
                  <X size={15} />
                  Cancel
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel this booking?</AlertDialogTitle>
                  <AlertDialogDescription>
                    The slot will be released for others to take. This cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep booking</AlertDialogCancel>
                  <AlertDialogAction onClick={onCancel}>Cancel booking</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function BookingsPage() {
  const { user, isAdmin } = useAuth()
  const [status, setStatus] = useState<BookingStatus | typeof ALL>(ALL)

  const { data: bookings, error, isLoading, refetch } = useAsync(
    () => bookingApi.list({ status: status === ALL ? undefined : status, limit: 100 }),
    [status],
  )

  const { run: cancel, isPending: isCancelling } = useMutation((id: number) =>
    bookingApi.cancel(id),
  )

  async function handleCancel(booking: Booking) {
    const result = await cancel(booking.id)
    if (!result) {
      toast.error('Could not cancel that booking')
      return
    }
    toast.success('Booking cancelled')
    refetch()
  }

  const list = bookings ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bookings"
        description={
          isAdmin
            ? 'Every booking across the platform.'
            : user?.role === 'owner'
              ? 'Bookings on your pitches, plus any you made yourself.'
              : 'Your upcoming and past bookings.'
        }
        actions={
          <Select
            value={status}
            onValueChange={(value) => setStatus(value as BookingStatus | typeof ALL)}
          >
            <SelectTrigger className="w-40" aria-label="Filter by status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {(Object.keys(BOOKING_STATUS_LABEL) as BookingStatus[]).map((value) => (
                <SelectItem key={value} value={value}>
                  {BOOKING_STATUS_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {isLoading ? (
        <OrbPanel state="searching" label="Loading bookings" />
      ) : error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : list.length === 0 ? (
        <EmptyState
          orbState="shaping"
          title={status === ALL ? 'No bookings yet' : `No ${status} bookings`}
          description={
            status === ALL
              ? 'Find a pitch and reserve a slot to get started.'
              : 'Try a different status filter.'
          }
          action={
            status === ALL ? (
              <Button asChild>
                <Link to="/">
                  <MapPin size={15} />
                  Browse turfs
                </Link>
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setStatus(ALL)}>
                Show all
              </Button>
            )
          }
        />
      ) : (
        <div className="space-y-3">
          {list.map((booking) => (
            <BookingCard
              key={booking.id}
              booking={booking}
              canCancel={canCancelBooking(booking.status)}
              isCancelling={isCancelling}
              onCancel={() => void handleCancel(booking)}
            />
          ))}
        </div>
      )}

      {isAdmin ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Kanban size={13} />
          Admins can also change status and mark payment from the API.
        </p>
      ) : null}
    </div>
  )
}
