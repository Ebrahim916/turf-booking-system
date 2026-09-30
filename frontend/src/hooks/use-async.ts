import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '@/lib/api'

type AsyncState<T> = {
  data: T | null
  error: ApiError | null
  isLoading: boolean
  refetch: () => void
}

/**
 * Minimal data-fetching hook. Deliberately not a caching library: every list in
 * this app is small, user-scoped, and invalidated explicitly after a mutation,
 * so a request cache would add moving parts without buying anything.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: readonly unknown[],
  options: { enabled?: boolean } = {},
): AsyncState<T> {
  const { enabled = true } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [isLoading, setIsLoading] = useState(enabled)
  const [nonce, setNonce] = useState(0)

  // Callers pass an inline arrow, so the fetcher's identity changes every
  // render. It is held in a ref and synced in an effect declared *before* the
  // fetching effect, so the ref is always current when the fetch runs. Writing
  // `ref.current` during render is avoided — that is not a supported pattern and
  // it breaks under concurrent rendering.
  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  })

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false)
      return
    }

    let cancelled = false
    setIsLoading(true)
    setError(null)

    fnRef
      .current()
      .then((result) => {
        if (cancelled) return
        setData(result)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError(0, null, cause instanceof Error ? cause.message : 'Request failed'),
        )
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, nonce])

  const refetch = useCallback(() => setNonce((n) => n + 1), [])

  return { data, error, isLoading, refetch }
}

type MutationState<TArgs, TResult> = {
  run: (args: TArgs) => Promise<TResult | null>
  isPending: boolean
  error: ApiError | null
  reset: () => void
}

/**
 * Wraps a write call with pending/error state and normalises thrown errors.
 *
 * `TArgs` defaults to `void` so that a zero-argument mutation can be triggered
 * with a bare `run()`; TypeScript allows omitting a `void` parameter.
 */
export function useMutation<TArgs = void, TResult = void>(
  fn: (args: TArgs) => Promise<TResult>,
): MutationState<TArgs, TResult> {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  })

  const run = useCallback(async (args: TArgs) => {
    setIsPending(true)
    setError(null)
    try {
      return await fnRef.current(args)
    } catch (cause) {
      const apiError =
        cause instanceof ApiError
          ? cause
          : new ApiError(0, null, cause instanceof Error ? cause.message : 'Request failed')
      setError(apiError)
      return null
    } finally {
      setIsPending(false)
    }
  }, [])

  const reset = useCallback(() => setError(null), [])

  return { run, isPending, error, reset }
}

/** Debounces a rapidly-changing value, e.g. a search box. */
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

/**
 * A clock that ticks on an interval.
 *
 * Reading `Date.now()` during render is impure: it can disagree between renders
 * and yields a stale result, which matters here because "is this slot already
 * in the past?" must neither flicker nor freeze. Holding the value in state and
 * refreshing it on a timer keeps every render consistent, and stops an
 * open booking page from advertising slots that have since elapsed.
 */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs])

  return now
}
