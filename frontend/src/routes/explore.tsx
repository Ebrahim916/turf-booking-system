import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TurfCard } from '@/components/turf-card'
import { EmptyState, ErrorState, PageHeader } from '@/components/feedback'
import { OrbPanel } from '@/components/orb-loader'
import { useAsync, useDebounced } from '@/hooks/use-async'
import { useAuth } from '@/lib/auth-context'
import { turfApi } from '@/lib/endpoints'
import { Search } from '@/components/animate-ui/icons/search'
import { X } from '@/components/animate-ui/icons/x'
import { Compass } from '@/components/animate-ui/icons/compass'

export function ExplorePage() {
  const { user } = useAuth()
  const [cityInput, setCityInput] = useState('')
  const city = useDebounced(cityInput.trim(), 350)

  const { data: turfs, error, isLoading, refetch } = useAsync(
    () => turfApi.list({ city: city || undefined, limit: 100 }),
    [city],
  )

  return (
    <div className="space-y-8">
      {user ? null : (
        <section className="rounded-xl border border-border bg-surface-muted px-6 py-10">
          <p className="text-sm font-medium text-muted-foreground">Turf Booking</p>
          <h1 className="mt-2 max-w-xl text-3xl font-semibold tracking-tight">
            Book a pitch by the hour.
          </h1>
          <p className="mt-3 max-w-lg text-sm text-muted-foreground">
            Browse available grounds, pick an open slot, and pay on site. No account needed to
            look around.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Button size="lg" asChild>
              <Link to="/register">Create an account</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </section>
      )}

      <div className="space-y-4">
        <PageHeader
          title="Available turfs"
          description={
            city ? `Showing results in ${city}.` : 'Every active pitch, with live availability.'
          }
        />

        <div className="relative max-w-sm">
          <Search
            size={16}
            className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            value={cityInput}
            onChange={(event) => setCityInput(event.target.value)}
            placeholder="Filter by city"
            aria-label="Filter turfs by city"
            className="pr-9 pl-9"
          />
          {cityInput ? (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Clear city filter"
              className="absolute top-1/2 right-1.5 -translate-y-1/2"
              onClick={() => setCityInput('')}
            >
              <X size={14} />
            </Button>
          ) : null}
        </div>
      </div>

      {isLoading ? (
        <OrbPanel state="searching" label="Finding turfs" />
      ) : error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : turfs && turfs.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {turfs.map((turf) => (
            <TurfCard key={turf.id} turf={turf} />
          ))}
        </div>
      ) : (
        <EmptyState
          orbState="shaping"
          title={city ? `No turfs in ${city}` : 'No turfs published yet'}
          description={
            city
              ? 'Try a different city, or clear the filter to see everything.'
              : 'Once an owner publishes a pitch it will appear here.'
          }
          action={
            city ? (
              <Button variant="outline" onClick={() => setCityInput('')}>
                Clear filter
              </Button>
            ) : (
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <Compass size={14} />
                Check back soon
              </span>
            )
          }
        />
      )}
    </div>
  )
}
