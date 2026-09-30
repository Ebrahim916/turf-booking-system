import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/feedback'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60dvh] items-center justify-center">
      <EmptyState
        orbState="shaping"
        title="Page not found"
        description="That URL does not match anything in the app."
        action={
          <Button asChild>
            <Link to="/">Back to turfs</Link>
          </Button>
        }
      />
    </div>
  )
}
