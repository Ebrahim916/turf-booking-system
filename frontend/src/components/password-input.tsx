import { useState } from 'react'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Lock } from '@/components/animate-ui/icons/lock'
import { LockKeyholeOpen } from '@/components/animate-ui/icons/lock-keyhole-open'
import { cn } from '@/lib/utils'

/**
 * The animate-ui registry has no `eye`/`eye-off`, so the reveal toggle borrows
 * the lock pair: closed for hidden, unlocked for visible. The two read as a
 * matched state change rather than two unrelated glyphs.
 */
export function PasswordInput({
  className,
  ...props
}: React.ComponentProps<typeof Input>) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="relative">
      <Input
        {...props}
        type={visible ? 'text' : 'password'}
        className={cn('pr-10', className)}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        className="absolute top-1/2 right-1.5 -translate-y-1/2 text-muted-foreground"
        onClick={() => setVisible((current) => !current)}
      >
        {visible ? <LockKeyholeOpen size={15} /> : <Lock size={15} />}
      </Button>
    </div>
  )
}
