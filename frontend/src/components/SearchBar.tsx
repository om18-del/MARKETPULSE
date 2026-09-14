import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../api'
import type { Instrument } from '../types'

export function SearchBar({ autoFocus = false }: { autoFocus?: boolean }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Instrument[]>([])
  const [open, setOpen] = useState(false)
  const [hl, setHl] = useState(0)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const nav = useNavigate()

  useEffect(() => {
    const t = setTimeout(async () => {
      if (q.trim().length < 1) {
        setResults([])
        return
      }
      setLoading(true)
      try {
        const res = await api.search(q)
        setResults(res.results)
        setOpen(true)
        setHl(0)
      } finally {
        setLoading(false)
      }
    }, 180)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const go = (inst: Instrument) => {
    setOpen(false)
    setQ('')
    nav(`/asset/${inst.id}`)
  }

  return (
    <div className="search-wrap" style={{ width: '100%' }}>
      <Search className="search-icon" size={17} />
      <input
        ref={inputRef}
        className="search-input"
        value={q}
        autoFocus={autoFocus}
        placeholder="Search any stock or index — RELIANCE, AAPL, TSLA, NIFTY 50…"
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 180)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') setHl((h) => Math.min(h + 1, results.length - 1))
          if (e.key === 'ArrowUp') setHl((h) => Math.max(0, h - 1))
          if (e.key === 'Enter' && results[hl]) go(results[hl])
          if (e.key === 'Escape') setOpen(false)
        }}
        aria-label="Search stocks and indices"
      />
      {open && (results.length > 0 || loading) ? (
        <div className="search-drop">
          {loading && !results.length ? <div className="search-item muted">searching…</div> : null}
          {results.map((r, i) => (
            <div
              key={r.id}
              className={`search-item ${i === hl ? 'hl' : ''}`}
              onMouseDown={() => go(r)}
              onMouseEnter={() => setHl(i)}
            >
              <span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span>
              <span className="chip">{r.category} · {r.region}</span>
            </div>
          ))}
          {!loading && !results.length ? <div className="search-item muted">No match — try a symbol like “aapl” or “nifty”.</div> : null}
          <div className="faint" style={{ padding: '6px 16px 10px' }}>
            press <kbd>↑</kbd><kbd>↓</kbd> to navigate · <kbd>enter</kbd> to open · <kbd>Ctrl K</kbd> anywhere
          </div>
        </div>
      ) : null}
    </div>
  )
}
