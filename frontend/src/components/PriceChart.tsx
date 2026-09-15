import { useEffect, useMemo, useRef, useState } from 'react'
import { createChart, ColorType, AreaSeries, type IChartApi, type UTCTimestamp, type Time } from 'lightweight-charts'

type Bar = { time: string; close: number }

/**
 * 'YYYY-MM-DD' stays a business-day string; 'YYYY-MM-DD HH:MM' (IST wall
 * clock) becomes a UTC epoch so the axis shows the IST session time —
 * the same convention the TimeframeStats chart uses.
 */
function toChartTime(raw: string): number | string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
  if (!m) return raw.slice(0, 10)
  const [, y, mo, d, h, mi] = m.map(Number) as unknown as number[]
  return Math.floor(Date.UTC(y, mo - 1, d, h, mi) / 1000) as UTCTimestamp
}

/** Strictly-ascending, unique timestamps — the library hard-throws otherwise. */
function toPoints(bars: Bar[]): { time: Time; value: number }[] {
  const sorted = [...bars]
    .filter((b) => b.close != null && b.time)
    .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
  const points: { time: Time; value: number }[] = []
  let prev: string | number = ''
  for (const b of sorted) {
    const t = toChartTime(b.time)
    if (t <= prev) continue
    points.push({ time: t as Time, value: b.close })
    prev = t
  }
  return points
}

const TABS = [
  { key: 'intraday', label: '5M' },
  { key: 'daily', label: 'Daily' },
  { key: 'monthly', label: 'Monthly' },
] as const

export function PriceChart({ initialBars, instrumentId }: { initialBars: Bar[]; instrumentId: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [tf, setTf] = useState<'intraday' | 'daily' | 'monthly'>('daily')
  const [bars, setBars] = useState<Bar[]>(initialBars)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [note, setNote] = useState('daily closes · official exchange files')

  useEffect(() => {
    // New asset: reset to daily and adopt its bars without a refetch.
    setTf('daily')
    setBars(initialBars)
    setErr(null)
    setNote('daily closes · official exchange files')
  }, [instrumentId, initialBars])

  useEffect(() => {
    if (tf === 'daily') return // daily bars already in hand from /api/asset
    let cancelled = false
    setLoading(true)
    setErr(null)
    fetch(`/api/chart/${encodeURIComponent(instrumentId)}?tf=${tf}`)
      .then(async (r) => {
        const j = await r.json()
        if (cancelled) return
        if (!r.ok || !j.available) {
          setErr(j.reason ?? `unavailable (${r.status})`)
          setBars([])
          return
        }
        setBars(j.bars)
        setNote(j.interval_note ?? '')
      })
      .catch((e) => {
        if (!cancelled) setErr(e?.message ?? 'failed to load bars')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [tf, instrumentId])

  const points = useMemo(() => toPoints(bars), [bars])

  useEffect(() => {
    if (!ref.current) return
    if (points.length < 2) return
    const chart = createChart(ref.current, {
      height: 380,
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
      timeScale: {
        borderColor: 'rgba(147,160,184,0.15)',
        visible: true,
        timeVisible: tf === 'intraday', // show HH:mm for the intraday view
        secondsVisible: false,
      },
      crosshair: { mode: 0 },
      // ResizeObserver-driven sizing: avoids measuring a 0-width container
      // during layout (which produced SVG <line> warnings on first paint).
      autoSize: true,
    })
    chartRef.current = chart

    const first = points[0].value
    const last = points[points.length - 1].value
    const rising = last >= first
    const series = chart.addSeries(AreaSeries, {
      lineColor: rising ? '#34d399' : '#fb7185',
      topColor: rising ? 'rgba(52,211,153,0.30)' : 'rgba(251,113,133,0.30)',
      bottomColor: 'rgba(52,211,153,0.0)',
      lineWidth: 2,
      priceLineVisible: false,
    })
    series.setData(points)
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [points, tf])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`btn ghost ${tf === t.key ? 'primary' : ''}`}
              style={{ padding: '3px 12px', fontSize: 12.5, border: '1px solid var(--card-border)' }}
              onClick={() => setTf(t.key)}
              aria-pressed={tf === t.key}
            >
              {t.label}
            </button>
          ))}
        </div>
        <span className="faint" style={{ fontSize: 11.5 }}>
          {loading ? 'loading…' : note}
        </span>
      </div>
      {err ? (
        <p className="muted">This timeframe isn't available for this asset ({err}). Daily is always available above.</p>
      ) : points.length >= 2 ? (
        <div ref={ref} style={{ width: '100%' }} />
      ) : (
        <p className="muted">Not enough history yet to draw a chart.</p>
      )}
    </div>
  )
}
