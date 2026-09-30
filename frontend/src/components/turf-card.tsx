import { Link } from 'react-router-dom'

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowRight } from '@/components/animate-ui/icons/arrow-right'
import { Gauge } from '@/components/animate-ui/icons/gauge'
import { MapPin } from '@/components/animate-ui/icons/map-pin'
import { formatMoney } from '@/lib/format'
import type { Turf } from '@/lib/types'

/**
 * Turfs have no photos yet (they are on the backend's "not yet built" list), so
 * the card leads with typography and metadata rather than a placeholder image.
 */
export function TurfCard({ turf }: { turf: Turf }) {
  const openDays = turf.schedules.filter((schedule) => schedule.is_active).length

  return (
    <Card className="group/turf relative transition-shadow hover:shadow-md">
      <CardHeader>
        <CardTitle>
          <Link to={`/turfs/${turf.id}`} className="after:absolute after:inset-0">
            {turf.name}
          </Link>
        </CardTitle>
        {turf.description ? (
          <p className="line-clamp-2 text-sm text-muted-foreground">{turf.description}</p>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-3">
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <MapPin size={15} className="mt-0.5 shrink-0" />
          <span>
            {turf.address}
            {turf.city ? `, ${turf.city}` : ''}
          </span>
        </p>

        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary" className="gap-1 font-normal">
            <Gauge size={12} />
            {turf.size}
          </Badge>
          {turf.surface ? (
            <Badge variant="secondary" className="font-normal">
              {turf.surface}
            </Badge>
          ) : null}
          <Badge variant="secondary" className="font-normal">
            {turf.slot_duration_minutes} min slots
          </Badge>
        </div>
      </CardContent>

      <CardFooter className="justify-between">
        <p className="text-sm">
          <span className="font-semibold">{formatMoney(turf.price_per_hour)}</span>
          <span className="text-muted-foreground"> / hour</span>
        </p>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          {openDays > 0 ? `${openDays} open day${openDays === 1 ? '' : 's'}` : 'No hours set'}
          <ArrowRight
            size={14}
            className="transition-transform group-hover/turf:translate-x-0.5"
          />
        </span>
      </CardFooter>
    </Card>
  )
}
