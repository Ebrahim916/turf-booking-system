import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'
import { Moon } from '@/components/animate-ui/icons/moon'
import { Sun } from '@/components/animate-ui/icons/sun'

/**
 * `next-themes` writes the `dark` class onto <html>, which is the first layer
 * `ThinkingOrb`'s `theme="auto"` resolution looks for — so the orbs follow this
 * toggle without any explicit wiring.
 *
 * Both glyphs are rendered and swapped with the `dark:` variant rather than
 * branching on `resolvedTheme` in JS. That avoids the usual mount-flag and its
 * cascading extra render, and sidesteps the server/client markup mismatch that
 * reading the resolved theme during the first render would cause.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
    >
      <Sun size={16} animateOnHover className="hidden dark:block" />
      <Moon size={16} animateOnHover className="block dark:hidden" />
    </Button>
  )
}
