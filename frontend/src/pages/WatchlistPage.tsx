import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, ArrowUpRight, AlertTriangle, StarOff } from 'lucide-react'
import { api, DISCLAIMER } from '../api'
import { useWatchlist } from '../hooks/useWatchlist'
import { CardSkeleton } from '../components/Skeletons'
import { EmptyState } from '../components/EmptyState'
import { IndexCard } from '../components/IndexCard'
import type { GridEntry } from '../types'

type Quote = GridEntry & { data_date: string }

const HINTS = ['nse-reliance', 'nse-tcs', 'nifty50', 'sensex', 'niftybank', 'usdinr']

export function WatchlistPage() {
  const watchlist = useWatchlist()
  const [quotes, setQuotes] = useState<Quote[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    if (!watchlist.items.length) {
      setQuotes([])
      return
    }
    setQuotes(null)
    setErr(null)
    api
      .watchlistQuotes(watchlist.items)
      .then((r) => {
        if (!cancelled) setQuotes(r.quotes)
      })
      .catch((e: Error) => {
        if (!cancelled) setErr(e.message ?? String(e))
      })
    return () => {
      cancelled = true
    }
  }, [watchlist.items, tick])

  if (!watchlist.items.length) {
    return (
      <div>
        <h1 className="page-title">My Watchlist</h1>
        <p className="muted" style={{ maxWidth: 560 }}>
          Track the assets you care about in one place. On any asset page, tap{' '}
          <strong>☆ Watch</strong> — or start with one of these:
        </p>
        <div className="card" style={{ marginTop: 16, padding: 18 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {HINTS.map((id) => (
              <Link key={id} to={`/asset/${id}`} className="btn ghost" style={{ padding: '6px 12px' }}>
                {id.replace(/^nse-/, '').toUpperCase()} <ArrowUpRight size={13} />
              </Link>
            ))}
          </div>
        </div>
        <p className="muted" style={{ marginTop: 18, fontSize: 12.5 }}>{DISCLAIMER}</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h1 className="page-title" style={{ margin: 0 }}>My Watchlist</h1>
        <span className="chip">{watchlist.items.length} saved</span>
        <button className="btn ghost" style={{ padding: '6px 12px' }} onClick={refresh}>
          Refresh
        </button>
      </div>
      <p className="muted" style={{ marginTop: 8, fontSize: 13 }}>
        Official EOD closes — Indian stocks come from NSE exchange files; indices update intraday.
      </p>

      {err ? (
        <div className="err-box" style={{ marginTop: 16 }} role="alert">
          <span className="err-box-icon"><AlertTriangle size={18} /></span>
          <span>Couldn&rsquo;t load quotes: {err}</span>
        </div>
      ) : quotes === null ? (
        <CardSkeleton height={320} />
      ) : quotes.length === 0 ? (
        <div style={{ marginTop: 16 }}>
          <EmptyState
            icon={<StarOff size={20} />}
            title="None of your saved assets resolved"
            action={
              <button className="btn primary" onClick={() => (window.location.href = '/')}>
                Find assets to add
              </button>
            }
          >
            The symbols in your watchlist may have been renamed or delisted. Browse the overview and
            add them again.
          </EmptyState>
        </div>
      ) : (
        <div className="grid cols-4" style={{ marginTop: 16 }}>
          {quotes.map((q, i) => (
            <IndexCard
              key={q.id}
              e={q}
              index={i}
              watched
              onToggleWatch={(id) => watchlist.toggle(id)}
            />
          ))}
        </div>
      )}

      <p className="muted" style={{ marginTop: 18, fontSize: 12.5 }}>{DISCLAIMER}</p>
      <p className="muted" style={{ fontSize: 12 }}>
        <Star size={11} style={{ verticalAlign: '-1px' }} /> Tip: prices refresh when you open the
        page — hit Refresh after the market closes for the newest official files.
      </p>
    </div>
  )
}
