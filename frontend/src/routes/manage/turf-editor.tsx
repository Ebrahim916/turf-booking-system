import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ErrorState, Hint, PageHeader } from '@/components/feedback'
import { OrbPanel } from '@/components/orb-loader'
import { useAsync, useMutation } from '@/hooks/use-async'
import { turfApi } from '@/lib/endpoints'
import {
  DAY_NAMES,
  dayShort,
  findOverlappingWindow,
  fromTimeInputValue,
  toTimeInputValue,
} from '@/lib/format'
import type { Schedule, TurfPayload } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ArrowLeft } from '@/components/animate-ui/icons/arrow-left'
import { Plus } from '@/components/animate-ui/icons/plus'
import { Trash2 } from '@/components/animate-ui/icons/trash-2'
import { Check } from '@/components/animate-ui/icons/check'
import { Clock } from '@/components/animate-ui/icons/clock'

const SIZE_OPTIONS = ['5-a-side', '7-a-side', '9-a-side', '11-a-side', 'Full pitch', 'Multi-sport']
const SLOT_OPTIONS = [30, 45, 60, 90, 120]

type FormState = {
  name: string
  description: string
  address: string
  city: string
  size: string
  surface: string
  price_per_hour: string
  slot_duration_minutes: string
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  address: '',
  city: '',
  size: '5-a-side',
  surface: '',
  price_per_hour: '',
  slot_duration_minutes: '60',
}

function SchedulesEditor({ turfId }: { turfId: number }) {
  const { data: schedules, error, isLoading, refetch } = useAsync(
    () => turfApi.listSchedules(turfId),
    [turfId],
  )

  const [day, setDay] = useState('0')
  const [openTime, setOpenTime] = useState('08:00')
  const [closeTime, setCloseTime] = useState('22:00')

  const { run: add, isPending: isAdding, error: addError } = useMutation(() =>
    turfApi.addSchedule(turfId, {
      day_of_week: Number(day),
      open_time: fromTimeInputValue(openTime),
      close_time: fromTimeInputValue(closeTime),
    }),
  )

  const { run: remove } = useMutation((scheduleId: number) =>
    turfApi.deleteSchedule(turfId, scheduleId),
  )

  const { run: toggle } = useMutation((input: { id: number; is_active: boolean }) =>
    turfApi.updateSchedule(turfId, input.id, { is_active: input.is_active }),
  )

  const { run: retime, error: retimeError } = useMutation(
    (input: { id: number; open_time: string; close_time: string }) =>
      turfApi.updateSchedule(turfId, input.id, {
        open_time: fromTimeInputValue(input.open_time),
        close_time: fromTimeInputValue(input.close_time),
      }),
  )

  async function handleAdd() {
    if (openTime >= closeTime) {
      toast.error('The closing time must be after the opening time')
      return
    }

    // The database rejects overlapping windows on the same day outright, so
    // catch it here to say why rather than surfacing a bare 409.
    const clash = findOverlappingWindow(
      schedules ?? [],
      Number(day),
      openTime,
      closeTime,
    )
    if (clash) {
      toast.error(
        `That overlaps the existing ${dayShort(clash.day_of_week)} window (${toTimeInputValue(clash.open_time)}–${toTimeInputValue(clash.close_time)}).`,
      )
      return
    }

    const created = await add()
    if (!created) return
    toast.success('Availability window added')
    refetch()
  }

  async function handleRemove(schedule: Schedule) {
    const result = await remove(schedule.id)
    if (!result) {
      toast.error('Could not remove that window')
      return
    }
    refetch()
  }

  async function handleToggle(schedule: Schedule) {
    const result = await toggle({ id: schedule.id, is_active: !schedule.is_active })
    if (!result) {
      toast.error('Could not update that window')
      return
    }
    refetch()
  }

  async function handleRetime(schedule: Schedule, field: 'open_time' | 'close_time', value: string) {
    const next = {
      id: schedule.id,
      open_time: field === 'open_time' ? value : toTimeInputValue(schedule.open_time),
      close_time: field === 'close_time' ? value : toTimeInputValue(schedule.close_time),
    }
    if (next.open_time >= next.close_time) {
      toast.error('The closing time must be after the opening time')
      return
    }
    const result = await retime(next)
    if (!result) {
      toast.error('Could not update the times')
      return
    }
    refetch()
  }

  if (isLoading) return <OrbPanel state="working" label="Loading availability" className="py-10" />
  if (error) return <ErrorState message={error.message} onRetry={refetch} />

  const list = schedules ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock size={16} className="text-muted-foreground" />
          Weekly availability
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Hint>
          Slots are generated from these windows at the pitch&rsquo;s slot length. Past slots and
          slots overlapping a live booking are marked unavailable automatically.
        </Hint>

        {list.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
            No windows yet. This pitch has no bookable slots until you add one.
          </p>
        ) : (
          <ul className="space-y-2">
            {list.map((schedule) => (
              <li
                key={schedule.id}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-border px-3 py-2"
              >
                <span
                  className={cn(
                    'w-12 text-sm font-medium',
                    !schedule.is_active && 'text-muted-foreground line-through',
                  )}
                >
                  {dayShort(schedule.day_of_week)}
                </span>

                <input
                  type="time"
                  aria-label={`Opening time for ${DAY_NAMES[schedule.day_of_week]}`}
                  defaultValue={toTimeInputValue(schedule.open_time)}
                  onBlur={(event) => {
                    if (event.target.value !== toTimeInputValue(schedule.open_time)) {
                      void handleRetime(schedule, 'open_time', event.target.value)
                    }
                  }}
                  className="rounded-md border border-input bg-transparent px-2 py-1 text-sm tabular-nums outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
                <span className="text-muted-foreground">–</span>
                <input
                  type="time"
                  aria-label={`Closing time for ${DAY_NAMES[schedule.day_of_week]}`}
                  defaultValue={toTimeInputValue(schedule.close_time)}
                  onBlur={(event) => {
                    if (event.target.value !== toTimeInputValue(schedule.close_time)) {
                      void handleRetime(schedule, 'close_time', event.target.value)
                    }
                  }}
                  className="rounded-md border border-input bg-transparent px-2 py-1 text-sm tabular-nums outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />

                <div className="ml-auto flex items-center gap-3">
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    Open
                    <Switch
                      checked={schedule.is_active}
                      onCheckedChange={() => void handleToggle(schedule)}
                      aria-label={`Toggle ${DAY_NAMES[schedule.day_of_week]} availability`}
                    />
                  </label>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Remove ${DAY_NAMES[schedule.day_of_week]} window`}
                    onClick={() => void handleRemove(schedule)}
                  >
                    <Trash2 size={15} />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {retimeError ? <FieldError>{retimeError.message}</FieldError> : null}

        <Separator />

        <div className="flex flex-wrap items-end gap-2">
          <Field className="w-32">
            <FieldLabel htmlFor="new-day">Day</FieldLabel>
            <Select value={day} onValueChange={setDay}>
              <SelectTrigger id="new-day" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DAY_NAMES.map((name, index) => (
                  <SelectItem key={name} value={String(index)}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field className="w-32">
            <FieldLabel htmlFor="new-open">Opens</FieldLabel>
            <Input
              id="new-open"
              type="time"
              value={openTime}
              onChange={(event) => setOpenTime(event.target.value)}
            />
          </Field>

          <Field className="w-32">
            <FieldLabel htmlFor="new-close">Closes</FieldLabel>
            <Input
              id="new-close"
              type="time"
              value={closeTime}
              onChange={(event) => setCloseTime(event.target.value)}
            />
          </Field>

          <Button onClick={handleAdd} disabled={isAdding}>
            <Plus size={15} animateOnTap />
            {isAdding ? 'Adding…' : 'Add window'}
          </Button>
        </div>

        {addError ? <FieldError>{addError.message}</FieldError> : null}
      </CardContent>
    </Card>
  )
}

export function TurfEditorPage() {
  const { turfId } = useParams<{ turfId: string }>()
  const isNew = !turfId
  const id = Number(turfId)
  const navigate = useNavigate()

  const existing = useAsync(
    () => (isNew ? Promise.resolve(null) : turfApi.get(id)),
    [id, isNew],
    { enabled: !isNew },
  )

  const [form, setForm] = useState<FormState | null>(null)

  const loaded = existing.data
  // Seed the form from the loaded turf, but never clobber edits the user has
  // already started making.
  const current: FormState =
    form ??
    (loaded
      ? {
          name: loaded.name,
          description: loaded.description ?? '',
          address: loaded.address,
          city: loaded.city ?? '',
          size: loaded.size,
          surface: loaded.surface ?? '',
          price_per_hour: String(Number(loaded.price_per_hour)),
          slot_duration_minutes: String(loaded.slot_duration_minutes),
        }
      : EMPTY_FORM)

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm({ ...current, [key]: value })
  }

  const { run: save, isPending, error } = useMutation(async (payload: TurfPayload) => {
    if (isNew) return turfApi.create(payload)
    return turfApi.update(id, payload)
  })

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()

    const price = Number.parseFloat(current.price_per_hour)
    if (!Number.isFinite(price) || price <= 0) {
      toast.error('Enter a price greater than zero')
      return
    }

    const payload: TurfPayload = {
      name: current.name,
      address: current.address,
      price_per_hour: price,
      description: current.description.trim() || null,
      city: current.city.trim() || null,
      surface: current.surface.trim() || null,
      size: current.size,
      slot_duration_minutes: Number(current.slot_duration_minutes),
    }

    const saved = await save(payload)
    if (!saved) return

    toast.success(isNew ? 'Turf created' : 'Turf updated')
    if (isNew) {
      navigate(`/manage/turfs/${saved.id}`, { replace: true })
    } else {
      existing.refetch()
    }
  }

  if (!isNew && existing.isLoading) {
    return <OrbPanel state="working" label="Loading turf" />
  }

  if (!isNew && existing.error) {
    return <ErrorState message={existing.error.message} onRetry={existing.refetch} />
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/manage/turfs">
          <ArrowLeft size={15} />
          My turfs
        </Link>
      </Button>

      <PageHeader
        title={isNew ? 'Add a turf' : (existing.data?.name ?? 'Edit turf')}
        description={
          isNew
            ? 'Describe the pitch and set your hourly rate.'
            : 'Update the details customers see when booking.'
        }
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="name">Name</FieldLabel>
                <Input
                  id="name"
                  required
                  minLength={2}
                  maxLength={150}
                  value={current.name}
                  onChange={(event) => update('name', event.target.value)}
                  placeholder="Riverside 5-a-side"
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="description">Description</FieldLabel>
                <Textarea
                  id="description"
                  rows={3}
                  maxLength={1000}
                  value={current.description}
                  onChange={(event) => update('description', event.target.value)}
                  placeholder="Surface type, lighting, changing rooms…"
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="address">Address</FieldLabel>
                <Input
                  id="address"
                  required
                  minLength={5}
                  maxLength={500}
                  value={current.address}
                  onChange={(event) => update('address', event.target.value)}
                />
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="city">City</FieldLabel>
                  <Input
                    id="city"
                    maxLength={100}
                    value={current.city}
                    onChange={(event) => update('city', event.target.value)}
                    placeholder="Used by the city filter"
                  />
                </Field>

                <Field>
                  <FieldLabel htmlFor="surface">Surface</FieldLabel>
                  <Input
                    id="surface"
                    maxLength={50}
                    value={current.surface}
                    onChange={(event) => update('surface', event.target.value)}
                    placeholder="Artificial turf"
                  />
                </Field>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <Field>
                  <FieldLabel htmlFor="size">Size</FieldLabel>
                  <Select value={current.size} onValueChange={(value) => update('size', value)}>
                    <SelectTrigger id="size" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SIZE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>

                <Field>
                  <FieldLabel htmlFor="price">Price per hour</FieldLabel>
                  <Input
                    id="price"
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    inputMode="decimal"
                    value={current.price_per_hour}
                    onChange={(event) => update('price_per_hour', event.target.value)}
                    placeholder="800"
                  />
                </Field>

                <Field>
                  <FieldLabel htmlFor="slot">Slot length</FieldLabel>
                  <Select
                    value={current.slot_duration_minutes}
                    onValueChange={(value) => update('slot_duration_minutes', value)}
                  >
                    <SelectTrigger id="slot" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SLOT_OPTIONS.map((minutes) => (
                        <SelectItem key={minutes} value={String(minutes)}>
                          {minutes} minutes
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              {error ? <FieldError>{error.message}</FieldError> : null}
            </FieldGroup>

            <div className="mt-6">
              <Button type="submit" disabled={isPending}>
                <Check size={15} animateOnTap />
                {isPending ? 'Saving…' : isNew ? 'Create turf' : 'Save changes'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>

      {isNew ? (
        <Hint>Save the pitch first, then add the weekly hours it is open.</Hint>
      ) : (
        <SchedulesEditor turfId={id} />
      )}
    </div>
  )
}
