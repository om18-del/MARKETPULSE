import { useEffect, useMemo, useRef, useState } from 'react'
import { createChart, ColorType, AreaSeries } from 'lightweight-charts'
import { TrendingUp, TrendingDown, Minus, Clock, CalendarDays, Zap, Activity } from 'lucide-react'

interface TFFactor {
  name: string
  value: string
  side: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  explain?: string
}

interface TFMetrics {
  last_close?: number
  period_open?: number
  period_low?: number
  period_high?: number
  period_return_pct?: number
  recent_return_pct?: number | null
  rsi14?: number | null
  sma20?: number | null
  ema9?: number | null
  ema21?: number | null
  macd_hist?: number | null
  bollinger_pos_pct?: number | null
  range_pos_pct?: number
  volatility_ann_pct?: number | null
  updown_volume?: number | null
  last_volume_vs_avg?: number | null
  bars?: number
  window?: string | null
}

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
  source?: string | null
  factors?: TFFactor[]
  metrics?: TFMetrics
  drivers?: string[]
  summary?: string
  chart?: { bars: { time: string; close: number }[]; interval_note: string }
}

interface TimeframePayload {
  yahoo_symbol?: string | null
  timeframes: { intraday: TFStat; daily: TFStat; monthly: TFStat }
  consensus?: { verdict?: string; note?: string }
}

const TABS = [
  { key: 'intraday', label: 'Intraday', icon: Clock, hint: '5-minute bars · last 5 sessions' },
  { key: 'daily', label: 'Daily', icon: Zap, hint: 'daily closes · last year' },
  { key: 'monthly', label: 'Monthly', icon: CalendarDays, hint: 'monthly closes · 10 years' },
] as const

type TabKey = (typeof TABS)[number]['key']

/* ------------------------------- chart --------------------------------- */

type Point = { time: number | string; value: number }

/** 'YYYY-MM-DD' stays a business-day string; 'YYYY-MM-DD HH:MM' (IST wall
 *  clock) becomes a UTC epoch so the axis shows the IST session time. */
function toChartTime(raw: string): number | string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
  if (!m) return raw.slice(0, 10)
  const [, y, mo, d, h, mi] = m.map(Number) as unknown as number[]
  return Math.floor(Date.UTC(y, mo - 1, d, h, mi) / 1000)
}

function TFChart({ bars, height = 260 }: { bars: { time: string; close: number }[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const points = useMemo<Point[]>(
    () =>
      bars
        .filter((b) => b.close != null)
        .map((b) => ({ time: toChartTime(b.time), value: b.close })),
    [bars],
  )

  useEffect(() => {
    if (!ref.current || points.length < 2) return
    const chart = createChart(ref.current, {
      height,
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#93a0b8',
        fontFamily: 'Inter, system-ui, sans-serif',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(147,160,184,0.08)' },
        horzLines: { color: 'rgba(147,160,184,0.08)' },
      },
      rightPriceScale: { borderColor: 'rgba(147,160,184,0.15)' },
      timeScale: { borderColor: 'rgba(147,160,184,0.15)', timeVisible: true },
      crosshair: { mode: 0 },
    })
    const first = points[0].value
    const lastP = points[points.length - 1].value
    const up = lastP >= first
    const series = chart.addSeries(AreaSeries, {
      lineColor: up ? '#34d399' : '#fb7185',
      topColor: up ? 'rgba(52,211,153,0.30)' : 'rgba(251,113,133,0.30)',
      bottomColor: 'rgba(0,0,0,0.0)',
      lineWidth: 2,
      priceLineVisible: false,
    })
    series.setData(points as never)
    chart.timeScale().fitContent()
    return () => { chart.remove() }
  }, [points, height])

  if (points.length < 2) return <p className="muted">Not enough bars to chart this timeframe.</p>
  return <div ref={ref} style={{ width: '100%' }} />
}

/* ------------------------------ sub-views ------------------------------- */

function SideIcon({ side }: { side?: string }) {
  if (side === 'BULLISH') return <TrendingUp size={13} style={{ color: 'var(--pos)', flexShrink: 0 }} />
  if (side === 'BEARISH') return <TrendingDown size={13} style={{ color: 'var(--neg)', flexShrink: 0 }} />
  return <Minus size={13} style={{ color: 'var(--text-faint)', flexShrink: 0 }} />
}

const fmt = (v?: number | null, d = 2) =>
  v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: d })

function MetricsGrid({ m, kind }: { m: TFMetrics; kind: string }) {
  const items: { k: string; v: string; tone?: 'pos' | 'neg' }[] = [
    { k: 'Close', v: fmt(m.last_close) },
    { k: 'Open', v: fmt(m.period_open) },
    { k: 'Low – High', v: `${fmt(m.period_low)} – ${fmt(m.period_high)}` },
    { k: `${kind} return`, v: `${(m.period_return_pct ?? 0) >= 0 ? '+' : ''}${fmt(m.period_return_pct)}%`, tone: (m.period_return_pct ?? 0) >= 0 ? 'pos' : 'neg' },
    { k: 'Recent move', v: m.recent_return_pct == null ? '—' : `${m.recent_return_pct >= 0 ? '+' : ''}${fmt(m.recent_return_pct)}%`, tone: (m.recent_return_pct ?? 0) >= 0 ? 'pos' : 'neg' },
    { k: 'RSI(14)', v: fmt(m.rsi14, 1) },
    { k: 'SMA20', v: fmt(m.sma20) },
    { k: 'EMA 9 / 21', v: `${fmt(m.ema9)} / ${fmt(m.ema21)}` },
    { k: 'MACD hist', v: m.macd_hist == null ? '—' : m.macd_hist.toFixed(2) },
    { k: 'Band position', v: m.bollinger_pos_pct == null ? '—' : `${m.bollinger_pos_pct}%` },
    { k: 'Range position', v: `${m.range_pos_pct ?? '—'}%` },
    { k: 'Volatility (ann.)', v: m.volatility_ann_pct == null ? '—' : `${fmt(m.volatility_ann_pct, 1)}%` },
  ]
  if (kind !== 'monthly') {
    items.push({ k: 'Up/Down volume', v: m.updown_volume == null ? '—' : fmt(m.updown_volume) })
    items.push({ k: 'Last vol vs avg', v: m.last_volume_vs_avg == null ? '—' : `×${fmt(m.last_volume_vs_avg)}` })
  }
  items.push({ k: 'Bars used', v: String(m.bars ?? '—') })

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 8 }}>
      {items.map((it) => (
        <div key={it.k} className="card" style={{ padding: '8px 10px' }}>
          <div className="faint" style={{ fontSize: 11 }}>{it.k}</div>
          <div style={{ fontWeight: 700, fontSize: 14, color: it.tone === 'pos' ? 'var(--pos)' : it.tone === 'neg' ? 'var(--neg)' : undefined }}>
            {it.v}
          </div>
        </div>
      ))}
    </div>
  )
}

function TFPanel({ tf }: { tf: TFStat }) {
  const [showWhy, setShowWhy] = useState(true)
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
      {/* verdict row */}
      <div className="card" style={{ padding: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 800, fontSize: 18, color: labelColor }}>{tf.label}</span>
          <span className="chip">{tf.confidence}% confidence</span>
          <span className="chip">score {tf.score}</span>
          {tf.source ? <span className="chip">src: {tf.source}</span> : null}
        </div>

        {/* battle bar */}
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
        <p className="muted" style={{ marginTop: 10, marginBottom: 0, fontSize: 13.5 }}>{tf.summary}</p>
      </div>

      {/* the per-timeframe chart */}
      {tf.chart?.bars?.length ? (
        <div className="card" style={{ padding: 14, marginTop: 10 }}>
          <div className="card-title" style={{ fontSize: 13 }}>
            <Activity size={13} /> {tf.kind} price action
            <span className="faint" style={{ fontWeight: 400, marginLeft: 8 }}>{tf.chart.interval_note}</span>
          </div>
          <TFChart bars={tf.chart.bars} />
        </div>
      ) : null}

      {/* hard numbers */}
      {tf.metrics ? (
        <div style={{ marginTop: 10 }}>
          <div className="card-title" style={{ fontSize: 13, marginBottom: 6 }}>The numbers behind the verdict</div>
          <MetricsGrid m={tf.metrics} kind={tf.kind} />
        </div>
      ) : null}

      {/* factor-by-factor with explanations */}
      <div className="card" style={{ padding: 14, marginTop: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-title" style={{ fontSize: 13, margin: 0 }}>Every signal, explained</div>
          <button className="btn ghost" style={{ padding: '3px 8px', fontSize: 12 }} onClick={() => setShowWhy((s) => !s)}>
            {showWhy ? 'Hide explanations' : 'Show explanations'}
          </button>
        </div>
        {(tf.factors ?? []).map((f, i) => (
          <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--card-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13.5 }}>
              <SideIcon side={f.side} />
              <span style={{ fontWeight: 600 }}>{f.name}</span>
              <span className="muted">{f.value}</span>
              <span style={{ marginLeft: 'auto', fontWeight: 700, fontSize: 12, color: f.side === 'BULLISH' ? 'var(--pos)' : f.side === 'BEARISH' ? 'var(--neg)' : 'var(--text-faint)' }}>
                {f.side}
              </span>
            </div>
            {showWhy && f.explain ? (
              <p className="faint" style={{ margin: '4px 0 0 21px', fontSize: 12.5, lineHeight: 1.45 }}>{f.explain}</p>
            ) : null}
          </div>
        ))}
        <p className="faint" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
          Computed purely from the {tf.metrics?.bars ?? '—'} {tf.kind} bars — no AI in this table, fully reproducible.
        </p>
      </div>
    </div>
  )
}

/* ------------------------------ main ------------------------------------ */

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
      {/* consensus strip */}
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

      {/* tabs */}
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
