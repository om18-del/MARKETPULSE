import { useCallback, useEffect, useState } from 'react'

const KEY = 'marketpulse.watchlist'

export function useWatchlist() {
  const [items, setItems] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(KEY) ?? '[]') as string[]
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(items))
  }, [items])

  const toggle = useCallback((id: string) => {
    setItems((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  }, [])

  const has = useCallback((id: string) => items.includes(id), [items])

  return { items, toggle, has }
}
