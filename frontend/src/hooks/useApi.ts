import { useCallback, useEffect, useRef, useState } from 'react'

/** Stale-while-revalidate data hook: caches last good payload per key in
 * sessionStorage, shows it instantly, refreshes in background. */
const memoryCache = new Map<string, unknown>()

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(() =>
    path ? ((memoryCache.get(path) as T) ?? null) : null,
  )
  const [loading, setLoading] = useState<boolean>(data === null && path !== null)
  const [error, setError] = useState<string | null>(null)
  const [fetchedAt, setFetchedAt] = useState<number | null>(null)
  const alive = useRef(true)

  const run = useCallback(async () => {
    if (!path) return
    setLoading((data) => data === null)
    setError(null)
    try {
      const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
      const res = await fetch(`${base}${path}`)
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error((detail as { detail?: string }).detail ?? `${res.status} ${res.statusText}`)
      }
      const json = (await res.json()) as T
      memoryCache.set(path, json)
      if (alive.current) {
        setData(json)
        setFetchedAt(Date.now())
      }
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (alive.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path])

  useEffect(() => {
    alive.current = true
    run()
    return () => {
      alive.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])

  return { data, loading, error, fetchedAt, refetch: run }
}
