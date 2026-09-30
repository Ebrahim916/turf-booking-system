import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState, ErrorState, Hint, PageHeader } from '@/components/feedback'
import { OrbPanel, OrbSlotGrid } from '@/components/orb-loader'
import { useAsync, useMutation, useNow } from '@/hooks/use-async'
import { useAuth } from '@/lib/auth-context'
import { bookingApi, turfApi } from '@/lib/endpoints'
import {
  addDaysUtc,
  dayShort,
  formatLongDate,
  formatMoney,
  formatTimeRange,
  todayUtc,
} from '@/lib/format'
import type { Slot } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ArrowLeft } from '@/components/animate-ui/icons/arrow-left'
import { ChevronLeft } from '@/components/animate-ui/icons/chevron-left'
import { ChevronRight } from '@/components/animate-ui/icons/chevron-right'
import { Clock } from '@/components/animate-ui/icons/clock'
import { Gauge } from '@/components/animate-ui/icons/gauge'
import { MapPin } from '@/components/animate-ui/icons/map-pin'
import { CircleCheckBig } from '@/components/animate-ui/icons/circle-check-big'
import { LogIn } from '@/components/animate-ui/icons/log-in'
import { Pause } from '@/components/animate-ui/icons/pause'
import { MessageCircleWarning } from '@/components/animate-ui/icons/message-circle-warning'

/** How far ahead the date strip lets a user plan. */
const BOOKING_HORIZON_DAYS = 14

export function TurfDetailPage() {
  const { turfId } = useParams<{ turfId: string }>()
  const id = Number(turfId)
  const { user } = useAuth()
  const navigate = useNavigate()

  const [selectedDate, setSelectedDate] = useState(todayUtc)
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null)
  const [notes, setNotes] = useState('')

  // Drives the "Past" label on elapsed slots; re-read each minute so a page
  // left open does not keep offering slots that have since gone by.
  const now = useNow()

  const dates = useMemo(
    () =>
      Array.from({ length: BOOKING_HORIZON_DAYS }, (_, offset) => {
        const value = addDaysUtc(todayUtc(), offset)
        return { value, weekday: new Date(`${value}T00:00:00Z`).getUTCDay() }
      }),
    [],
  )

  const turfQuery = useAsync(
    () => (Number.isFinite(id) ? turfApi.get(id) : Promise.reject(new Error('Invalid turf id'))),
    [id],
  )

  const turf = turfQuery.data

  const slotsQuery = useAsync(
    () => (Number.isFinite(id) ? turfApi.availability(id, selectedDate) : Promise.resolve([])),
    [id, selectedDate],
    { enabled: Number.isFinite(id) },
  )

  const { run: book, isPending: isBooking, error: bookError, reset: resetBookError } =
    useMutation((slot: Slot) =>
      bookingApi.create({
        turf_id: id,
        // Both ends are sent explicitly so the booking covers exactly the slot
        // the user saw, rather than re-deriving the duration server-side.
        start_time: slot.start_time,
        end_time: slot.end_time,
        notes: notes.trim() || null,
      }),
    )

  function shiftDate(days: number) {
    const next = addDaysUtc(selectedDate, days)
    // Stop at the ends of the horizon rather than wrapping around it.
    if (next < dates[0].value || next > dates[dates.length - 1].value) return
    setSelectedDate(next)
    setSelectedSlot(null)
    resetBookError()
  }

  async function handleBook() {
    if (!selectedSlot) return

    const created = await book(selectedSlot)
    if (!created) {
      // Losing the overlap race returns 409. The grid on screen is now stale —
      // someone else holds that slot — so refresh it and drop the selection
      // rather than leaving a button that looks bookable but always fails.
      if (bookError?.isBookingConflict) {
        toast.error('That slot was just taken', {
          description: 'The availability list has been refreshed.',
        })
        setSelectedSlot(null)
        slotsQuery.refetch()
      }
      return
    }

    toast.success('Slot booked', { description: 'Pay on site when you arrive.' })
    setSelectedSlot(null)
    setNotes('')
    navigate('/bookings')
  }

  if (turfQuery.isLoading) {
    return <OrbPanel state="searching" label="Loading pitch" />
  }

  if (turfQuery.error || !turf) {
    return (
      <ErrorState
        title="Pitch not found"
        message={turfQuery.error?.message ?? 'This pitch may have been removed.'}
        onRetry={turfQuery.refetch}
      />
    )
  }

  const slots = slotsQuery.data ?? []
  const available = slots.filter((slot) => slot.is_available)

  return (
    <div className="space-y-8">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/">
          <ArrowLeft size={15} />
          All turfs
        </Link>
      </Button>

      <PageHeader
        title={turf.name}
        description={turf.description ?? undefined}
        actions={
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <Badge variant="secondary" className="gap-1 font-normal">
              <Gauge size={12} />
              {turf.size}
            </Badge>
            {turf.surface ? (
              <Badge variant="secondary" className="font-normal">
                {turf.surface}
              </Badge>
            ) : null}
            <Badge variant="secondary" className="gap-1 font-normal">
              <Clock size={12} />
              {turf.slot_duration_minutes} min slots
            </Badge>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MapPin size={16} className="text-muted-foreground" />
                Location
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {turf.address}
                {turf.city ? `, ${turf.city}` : ''}
              </p>

              <Separator />

              <div>
                <p className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  Weekly hours
                </p>
                {turf.schedules.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No availability published for this pitch.
                  </p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {[...turf.schedules]
                      .sort((a, b) => a.day_of_week - b.day_of_week)
                      .map((schedule) => (
                        <li key={schedule.id} className="flex justify-between gap-4">
                          <span className={schedule.is_active ? '' : 'text-muted-foreground'}>
                            {dayShort(schedule.day_of_week)}
                          </span>
                          <span
                            className={cn(
                              'tabular-nums',
                              schedule.is_active ? '' : 'text-muted-foreground line-through',
                            )}
                          >
                            {schedule.open_time.slice(0, 5)} – {schedule.close_time.slice(0, 5)}
                          </span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pick a date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon-sm"
                  aria-label="Earlier dates"
                  disabled={selectedDate === dates[0].value}
                  onClick={() => shiftDate(-1)}
                >
                  <ChevronLeft size={15} />
                </Button>

                <div className="flex flex-1 gap-1.5 overflow-x-auto pb-1">
                  {dates.map((date) => (
                    <button
                      key={date.value}
                      type="button"
                      onClick={() => {
                        setSelectedDate(date.value)
                        setSelectedSlot(null)
                        resetBookError()
                      }}
                      aria-pressed={selectedDate === date.value}
                      className={cn(
                        'flex min-w-13 shrink-0 flex-col items-center gap-0.5 rounded-lg border px-2 py-1.5 text-xs transition-colors',
                        selectedDate === date.value
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
                      )}
                    >
                      <span>{dayShort((date.weekday + 6) % 7)}</span>
                      <span className="text-sm font-medium tabular-nums">
                        {Number(date.value.slice(8, 10))}
                      </span>
                    </button>
                  ))}
                </div>

                <Button
                  variant="outline"
                  size="icon-sm"
                  aria-label="Later dates"
                  disabled={selectedDate === dates[dates.length - 1].value}
                  onClick={() => shiftDate(1)}
                >
                  <ChevronRight size={15} />
                </Button>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                {formatLongDate(`${selectedDate}T00:00:00Z`)} · all times UTC
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Available slots</CardTitle>
            </CardHeader>
            <CardContent>
              {slotsQuery.isLoading ? (
                <OrbSlotGrid />
              ) : slotsQuery.error ? (
                <ErrorState message={slotsQuery.error.message} onRetry={slotsQuery.refetch} />
              ) : slots.length === 0 ? (
                <EmptyState
                  orbState="breathing"
                  title="Closed on this day"
                  description="This pitch has no availability window on the selected date. Try another day."
                />
              ) : available.length === 0 ? (
                <EmptyState
                  orbState="breathing"
                  title="Fully booked"
                  description="Every slot on this date is taken. Try the next day."
                />
              ) : (
                <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {slots.map((slot) => {
                    const isSelected = selectedSlot?.start_time === slot.start_time
                    // The API reports an unavailable slot as a bare
                    // `is_available: false` without saying why. Comparing
                    // against the clock separates "already gone" from "taken",
                    // which the user needs to tell apart.
                    const isPast = new Date(slot.start_time).getTime() <= now
                    const reason = isPast ? 'Past' : 'Booked'
                    return (
                      <button
                        key={slot.start_time}
                        type="button"
                        disabled={!slot.is_available}
                        onClick={() => {
                          setSelectedSlot(slot)
                          resetBookError()
                        }}
                        aria-pressed={isSelected}
                        className={cn(
                          'flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                          !slot.is_available && 'cursor-not-allowed border-border/60 opacity-45',
                          slot.is_available && isSelected && 'border-primary bg-accent text-accent-foreground',
                          slot.is_available &&
                            !isSelected &&
                            'border-border hover:border-primary/50 hover:bg-muted',
                        )}
                      >
                        <span className="font-medium tabular-nums">
                          {formatTimeRange(slot.start_time, slot.end_time)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {slot.is_available ? formatMoney(slot.total_price) : reason}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <aside className="lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Your booking</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rate</span>
                  <span className="tabular-nums">{formatMoney(turf.price_per_hour)} / hour</span>
                </div>
                {selectedSlot ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Slot</span>
                      <span className="tabular-nums">
                        {formatTimeRange(selectedSlot.start_time, selectedSlot.end_time)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Date</span>
                      <span>{selectedDate}</span>
                    </div>
                  </>
                ) : null}
              </div>

              <Separator />

              {/* Any non-conflict failure (validation, permissions, network)
                  is shown here; conflicts are handled as a toast in
                  `handleBook` because they also invalidate the slot grid. */}
              {bookError && !bookError.isBookingConflict ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                >
                  <MessageCircleWarning size={15} className="mt-0.5 shrink-0" />
                  {bookError.message}
                </p>
              ) : null}

              <div className="flex items-baseline justify-between">
                <span className="text-sm font-medium">Total</span>
                <span className="text-xl font-semibold tabular-nums">
                  {selectedSlot ? formatMoney(selectedSlot.total_price) : '—'}
                </span>
              </div>

              {user ? (
                <>
                  <div className="space-y-1.5">
                    <label htmlFor="notes" className="text-sm font-medium">
                      Notes <span className="text-muted-foreground">(optional)</span>
                    </label>
                    <Textarea
                      id="notes"
                      rows={2}
                      maxLength={500}
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="Anything the venue should know"
                    />
                  </div>

                  <Button
                    size="lg"
                    className="w-full"
                    disabled={!selectedSlot || isBooking}
                    onClick={handleBook}
                  >
                    {isBooking ? (
                      'Booking…'
                    ) : selectedSlot ? (
                      <>
                        <CircleCheckBig size={15} animateOnTap />
                        Book this slot
                      </>
                    ) : (
                      <>
                        <Pause size={15} />
                        Select a slot
                      </>
                    )}
                  </Button>

                  <Hint>Payment is cash on site. The slot is held the moment you confirm.</Hint>
                </>
              ) : (
                <div className="space-y-3">
                  <Button size="lg" className="w-full" asChild>
                    <Link to="/login" state={{ from: `/turfs/${turf.id}` }}>
                      <LogIn size={15} />
                      Sign in to book
                    </Link>
                  </Button>
                  <Hint>
                    Booking requires an account. It takes a moment to create one.
                  </Hint>
                </div>
              )}

              {!user ? (
                <p className="text-center text-xs text-muted-foreground">
                  No account?{' '}
                  <Link to="/register" className="underline underline-offset-4">
                    Create one
                  </Link>
                </p>
              ) : null}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
