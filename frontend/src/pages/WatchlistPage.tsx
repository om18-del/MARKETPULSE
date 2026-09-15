import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, Trash2, ArrowUpRight } from 'lucide-react'
import { api, DISCLAIMER } from '../api'
import { useWatchlist } from '../hooks/useWatchlist'
import { CardSkeleton } from '../components/Skeletons'

type Quote = {
  id: string
  name: string
  currency: string
  price: number
  change_pct: number
  data_date: string
  demo: boolean
}

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
        <div className="card" style={{ marginTop: 16, padding: 16, borderColor: 'var(--neg)' }}>
          Couldn't load quotes: {err}
        </div>
      ) : quotes === null ? (
        <CardSkeleton height={320} />
      ) : quotes.length === 0 ? (
        <div className="card" style={{ marginTop: 16, padding: 16 }}>
          None of the saved assets could be resolved — they may have been renamed. Remove them and
          re-add from search.
        </div>
      ) : (
        <div className="card" style={{ marginTop: 16, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--text-faint)', fontSize: 12 }}>
                <th style={{ padding: '10px 14px' }}>Asset</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Close</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Change</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Data date</th>
                <th style={{ padding: '10px 14px' }} aria-label="remove" />
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => {
                const up = q.change_pct >= 0
                return (
                  <tr key={q.id} style={{ borderTop: '1px solid var(--card-border)' }}>
                    <td style={{ padding: '11px 14px' }}>
                      <Link to={`/asset/${q.id}`} style={{ color: 'var(--text)', fontWeight: 600 }}>
                        {q.name}
                      </Link>
                      {q.demo ? <span className="chip demo" style={{ marginLeft: 8 }}>demo</span> : null}
                    </td>
                    <td className="num" style={{ padding: '11px 14px', textAlign: 'right', fontWeight: 700 }}>
                      {q.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      <span className="muted" style={{ fontSize: 11, marginLeft: 4 }}>{q.currency}</span>
                    </td>
                    <td
                      className="num"
                      style={{
                        padding: '11px 14px',
                        textAlign: 'right',
                        color: up ? 'var(--pos)' : 'var(--neg)',
                        fontWeight: 700,
                      }}
                    >
                      {up ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
                    </td>
                    <td className="muted" style={{ padding: '11px 14px', textAlign: 'right', fontSize: 12.5 }}>
                      {q.data_date}
                    </td>
                    <td style={{ padding: '11px 14px', textAlign: 'right' }}>
                      <button
                        className="btn ghost"
                        style={{ padding: '4px 8px' }}
                        onClick={() => watchlist.toggle(q.id)}
                        aria-label={`Remove ${q.name} from watchlist`}
                        title="Remove"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
