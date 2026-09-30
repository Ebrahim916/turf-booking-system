import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { EmptyState, ErrorState, PageHeader } from '@/components/feedback'
import { OrbPanel } from '@/components/orb-loader'
import { useAsync, useMutation } from '@/hooks/use-async'
import { turfApi } from '@/lib/endpoints'
import { dayShort, formatMoney } from '@/lib/format'
import type { Turf } from '@/lib/types'
import { Plus } from '@/components/animate-ui/icons/plus'
import { SlidersHorizontal } from '@/components/animate-ui/icons/sliders-horizontal'
import { Trash2 } from '@/components/animate-ui/icons/trash-2'
import { MapPin } from '@/components/animate-ui/icons/map-pin'

function TurfRow({ turf, onDeactivate }: { turf: Turf; onDeactivate: () => void }) {
  const openDays = turf.schedules.filter((schedule) => schedule.is_active).length

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/manage/turfs/${turf.id}`}
              className="font-medium underline-offset-4 hover:underline"
            >
              {turf.name}
            </Link>
            {!turf.is_active ? (
              <Badge variant="secondary" className="font-normal">
                Inactive
              </Badge>
            ) : null}
            <Badge variant="outline" className="font-normal">
              {turf.size}
            </Badge>
          </div>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin size={13} />
            {turf.address}
            {turf.city ? `, ${turf.city}` : ''}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatMoney(turf.price_per_hour)} / hour ·{' '}
            {openDays > 0
              ? turf.schedules
                  .filter((schedule) => schedule.is_active)
                  .map((schedule) => dayShort(schedule.day_of_week))
                  .join(', ')
              : 'no hours set'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/manage/turfs/${turf.id}`}>
              <SlidersHorizontal size={15} />
              Manage
            </Link>
          </Button>

          {turf.is_active ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="icon-sm" aria-label={`Deactivate ${turf.name}`}>
                  <Trash2 size={15} />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Deactivate “{turf.name}”?</AlertDialogTitle>
                  <AlertDialogDescription>
                    It will stop appearing in search and cannot be booked. Existing bookings are
                    left untouched.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep it active</AlertDialogCancel>
                  <AlertDialogAction onClick={onDeactivate}>Deactivate</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function ManageTurfsPage() {
  const { data: turfs, error, isLoading, refetch } = useAsync(() => turfApi.mine({ limit: 100 }), [])

  const { run: deactivate } = useMutation((id: number) => turfApi.deactivate(id))

  async function handleDeactivate(turf: Turf) {
    const result = await deactivate(turf.id)
    if (!result) {
      toast.error('Could not deactivate that pitch')
      return
    }
    toast.success(`${turf.name} deactivated`)
    refetch()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="My turfs"
        description="Pricing, weekly availability, and activation for the pitches you own."
        actions={
          <Button asChild>
            <Link to="/manage/turfs/new">
              <Plus size={15} animateOnTap />
              Add a turf
            </Link>
          </Button>
        }
      />

      {isLoading ? (
        <OrbPanel state="searching" label="Loading your turfs" />
      ) : error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : turfs && turfs.length > 0 ? (
        <div className="space-y-3">
          {turfs.map((turf) => (
            <TurfRow key={turf.id} turf={turf} onDeactivate={() => void handleDeactivate(turf)} />
          ))}
        </div>
      ) : (
        <EmptyState
          orbState="shaping"
          title="No turfs yet"
          description="Add your first pitch, then set the weekly hours it is open. Slots are generated from those hours."
          action={
            <Button asChild>
              <Link to="/manage/turfs/new">
                <Plus size={15} />
                Add a turf
              </Link>
            </Button>
          }
        />
      )}
    </div>
  )
}
