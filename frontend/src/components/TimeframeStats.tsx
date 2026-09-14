import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Clock, CalendarDays, Zap } from 'lucide-react'

interface TFStat {
  kind: string
  available: boolean
  reason?: string
  label?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  score?: number
  confidence?: number
  bull_count?: number
  bear_count?: number
  neutral_count?: number
  last_close?: number
  period_low?: number
  period_high?: number
  period_return_pct?: number
  bars?: number
  source?: string | null
  drivers?: string[]
  summary?: string
}

interface TimeframePayload {
  yahoo_symbol?: string | null
  timeframes: { intraday: TFStat; daily: TFStat; monthly: TFStat }
  consensus?: { verdict?: string; note?: string }
}

const TABS = [
  { key: 'intraday', label: 'Intraday', icon: Clock, hint: '5-minute bars' },
  { key: 'daily', label: 'Daily', icon: Zap, hint: 'daily closes' },
  { key: 'monthly', label: 'Monthly', icon: CalendarDays, hint: '10-year view' },
] as const

type TabKey = (typeof TABS)[number]['key']

function SideIcon({ side }: { side?: string }) {
  if (side === 'BULLISH') return <TrendingUp size={13} style={{ color: 'var(--pos)' }} />
  if (side === 'BEARISH') return <TrendingDown size={13} style={{ color: 'var(--neg)' }} />
  return <Minus size={13} style={{ color: 'var(--text-faint)' }} />
}

function TFPanel({ tf }: { tf: TFStat }) {
  if (!tf.available) {
    return (
      <div className="card" style={{ padding: 14 }}>
        <p className="muted" style={{ margin: 0 }}>
          {tf.kind[0].toUpperCase() + tf.kind.slice(1)} stats unavailable — {tf.reason}
        </p>
      </div>
    )
  }
  const labelColor =
    tf.label === 'BULLISH' ? 'var(--pos)' : tf.label === 'BEARISH' ? 'var(--neg)' : 'var(--neutral)'
  return (
    <div>
      <div className="card" style={{ padding: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 800, fontSize: 18, color: labelColor }}>{tf.label}</span>
          <span className="chip">{tf.confidence}% confidence</span>
          <span className="chip">score {tf.score}</span>
          {tf.source ? <span className="chip">src: {tf.source}</span> : null}
        </div>

        {/* Bull vs Bear stat battle-bar */}
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: 'var(--pos)', fontWeight: 700 }}>▲ {tf.bull_count} bullish</span>
            <span style={{ color: 'var(--text-faint)' }}>{tf.neutral_count} neutral</span>
            <span style={{ color: 'var(--neg)', fontWeight: 700 }}>{tf.bear_count} bearish ▼</span>
          </div>
          <div style={{ display: 'flex', height: 10, borderRadius: 5, overflow: 'hidden', gap: 2 }}>
            <div style={{ flex: tf.bull_count ?? 0, background: 'var(--pos)', opacity: 0.85 }} />
            <div style={{ flex: tf.neutral_count ?? 0, background: 'var(--text-faint)', opacity: 0.5 }} />
            <div style={{ flex: tf.bear_count ?? 0, background: 'var(--neg)', opacity: 0.85 }} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 12, fontSize: 13 }}>
          <span>Close <b>{(tf.last_close ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</b></span>
          <span>{tf.kind} range <b>{(tf.period_low ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} – {(tf.period_high ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}</b></span>
          <span>Return <b style={{ color: (tf.period_return_pct ?? 0) >= 0 ? 'var(--pos)' : 'var(--neg)' }}>
            {(tf.period_return_pct ?? 0) >= 0 ? '+' : ''}{tf.period_return_pct}%
          </b></span>
          <span className="faint">{tf.bars} bars</span>
        </div>
        <p className="muted" style={{ marginTop: 10, marginBottom: 0, fontSize: 13.5 }}>{tf.summary}</p>
      </div>

      <div className="card" style={{ padding: 14, marginTop: 10 }}>
        <div className="card-title" style={{ fontSize: 13 }}>Every signal, on this timeframe</div>
        {(tf.drivers ?? []).map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', fontSize: 13, borderBottom: '1px solid var(--card-border)' }}>
            <SideIcon side={d.split(':')[0]} />
            <span>{d}</span>
          </div>
        ))}
        <p className="faint" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
          Computed purely from the {tf.bars} {tf.kind} bars above — no AI, fully reproducible.
        </p>
      </div>
    </div>
  )
}

/**
 * Intraday · Daily · Monthly bullish/bearish stats with a consensus strip.
 * Fetches lazily on first tab open so the asset page stays fast.
 */
export function TimeframeStats({ instrumentId }: { instrumentId: string }) {
  const [data, setData] = useState<TimeframePayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabKey>('intraday')

  useEffect(() => {
    let dead = false
    setData(null)
    setError(null)
    fetch(`/api/timeframes/${encodeURIComponent(instrumentId)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j) => { if (!dead) setData(j) })
      .catch((e) => { if (!dead) setError(String(e.message || e)) })
    return () => { dead = true }
  }, [instrumentId])

  if (error) {
    return <div className="card" style={{ padding: 14 }}><p className="muted" style={{ margin: 0 }}>Timeframe stats unavailable — {error}</p></div>
  }
  if (!data) {
    return (
      <div className="card" style={{ padding: 14 }}>
        <p className="muted" style={{ margin: 0 }}>Computing intraday, daily and monthly signals…</p>
      </div>
    )
  }

  const c = data.consensus
  const cVerdict = c?.verdict
  const cColor = cVerdict === 'BULLISH' ? 'var(--pos)' : cVerdict === 'BEARISH' ? 'var(--neg)' : 'var(--neutral)'

  return (
    <div>
      {/* Consensus strip */}
      <div className="card" style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
        <span className="card-title" style={{ margin: 0, fontSize: 13 }}>CROSS-TIMEFRAME CONSENSUS</span>
        {cVerdict && cVerdict !== 'unavailable' ? (
          <>
            <span style={{ fontWeight: 800, color: cColor }}>{cVerdict}</span>
            <span className="muted" style={{ fontSize: 13 }}>{c?.note}</span>
          </>
        ) : (
          <span className="muted" style={{ fontSize: 13 }}>No timeframe data.</span>
        )}
        {data.yahoo_symbol ? <span className="chip">intraday via Yahoo · {data.yahoo_symbol}</span> : null}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        {TABS.map((t) => {
          const tf = data.timeframes[t.key]
          const active = tab === t.key
          const dot = tf?.available ? (tf.label === 'BULLISH' ? 'var(--pos)' : tf.label === 'BEARISH' ? 'var(--neg)' : 'var(--neutral)') : 'var(--text-faint)'
          return (
            <button
              key={t.key}
              className={`btn ${active ? '' : 'ghost'}`}
              onClick={() => setTab(t.key)}
              title={`${t.label} — ${t.hint}`}
            >
              <t.icon size={13} /> {t.label}
              <span style={{ width: 7, height: 7, borderRadius: 4, background: dot, display: 'inline-block', marginLeft: 4 }} />
            </button>
          )
        })}
      </div>

      <TFPanel tf={data.timeframes[tab]} />
    </div>
  )
}
