import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Radar, TrendingUp, TrendingDown } from 'lucide-react'

interface Conflict {
  symbol: string
  intraday: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  daily: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  intraday_ret?: number | null
  last_close?: number
  conflict: string
}

interface Payload {
  scanned?: number
  aligned?: number
  conflicts?: Conflict[]
  note?: string
  disclaimer?: string
}

export function ScannerPanel() {
  const [data, setData] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let dead = false
    fetch('/api/scanner/intraday-conflicts')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j) => { if (!dead) setData(j) })
      .catch((e) => { if (!dead) setErr(String(e.message || e)) })
    return () => { dead = true }
  }, [])

  return (
    <section className="section">
      <h2 className="card-title" style={{ fontSize: 15 }}><Radar size={15} /> Intraday ⟷ trend conflicts — reversal candidates</h2>
      {err ? (
        <div className="card" style={{ padding: 14 }}><p className="muted" style={{ margin: 0 }}>Scanner unavailable — {err}</p></div>
      ) : !data ? (
        <div className="card" style={{ padding: 14 }}><p className="muted" style={{ margin: 0 }}>Scanning NIFTY 50 intraday signals…</p></div>
      ) : (
        <div className="card" style={{ padding: 14 }}>
          <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
            NIFTY 50 stocks where today's <b>intraday direction opposes the daily trend</b> —
            the setups traders watch for trend exhaustion. {data.scanned} scanned · {data.aligned} aligned · {data.conflicts?.length ?? 0} conflicting.
          </p>
          {(data.conflicts?.length ?? 0) === 0 ? (
            <p className="muted" style={{ margin: 0 }}>No conflicts right now — every stock's intraday direction agrees with its daily trend.</p>
          ) : (
            <div>
              {data.conflicts!.map((c) => (
                <Link
                  key={c.symbol}
                  to={`/asset/nse-${c.symbol.toLowerCase()}`}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: '1px solid var(--card-border)' }}
                >
                  <span style={{ fontWeight: 700, width: 110 }}>{c.symbol}</span>
                  <span className={`chip ${c.intraday === 'BULLISH' ? 'pos' : 'neg'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {c.intraday === 'BULLISH' ? <TrendingUp size={11} /> : <TrendingDown size={11} />} intraday {c.intraday.toLowerCase()}
                  </span>
                  <span className="faint">vs</span>
                  <span className={`chip ${c.daily === 'BULLISH' ? 'pos' : 'neg'}`}>
                    daily {c.daily.toLowerCase()}
                  </span>
                  <span className="faint" style={{ marginLeft: 'auto', fontSize: 12.5 }}>{c.conflict}</span>
                  <span style={{ fontWeight: 700, fontSize: 13, color: (c.intraday_ret ?? 0) >= 0 ? 'var(--pos)' : 'var(--neg)', width: 64, textAlign: 'right' }}>
                    {(c.intraday_ret ?? 0) >= 0 ? '+' : ''}{c.intraday_ret?.toFixed(2)}%
                  </span>
                </Link>
              ))}
            </div>
          )}
          <p className="faint" style={{ marginTop: 10, marginBottom: 0, fontSize: 12 }}>{data.note}</p>
        </div>
      )}
    </section>
  )
}
