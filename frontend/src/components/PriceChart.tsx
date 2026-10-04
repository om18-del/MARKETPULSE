import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createChart, ColorType, AreaSeries, type IChartApi, type UTCTimestamp, type Time } from 'lightweight-charts'
import { chartChrome, seriesColors } from '../themeTokens'
import { clampZoomToData } from '../chartZoom'

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

const INTRADAY_POLL_MS = 60_000 // live graph: fresh 5-minute bars every minute

export function PriceChart({
  instrumentId,
  onLivePrice,
}: {
  instrumentId: string
  onLivePrice?: (price: number) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  // Live intraday is the default view — the graph moves in real time from
  // the first paint; Daily/Monthly are one click away.
  const [tf, setTf] = useState<'intraday' | 'daily' | 'monthly'>('intraday')
  const [bars, setBars] = useState<Bar[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [note, setNote] = useState('loading live session…')
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const loadTf = useCallback(
    async (t: 'intraday' | 'daily' | 'monthly', silent = false) => {
      if (!silent) setLoading(true)
      try {
        const r = await fetch(`/api/chart/${encodeURIComponent(instrumentId)}?tf=${t}`)
        const j = await r.json()
        if (!r.ok || !j.available) {
          if (!silent) {
            setErr(j.reason ?? `unavailable (${r.status})`)
            setBars([])
          }
          return
        }
        setErr(null)
        setBars(j.bars)
        setNote(j.interval_note ?? '')
        setUpdatedAt(new Date())
        if (t === 'intraday' && onLivePrice && j.bars?.length >= 2) {
          const last = j.bars[j.bars.length - 1]
          if (last?.close > 0) onLivePrice(last.close)
        }
      } catch {
        if (!silent) setErr('failed to load bars')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [instrumentId, onLivePrice],
  )

  // New asset: back to the live intraday view and load it.
  useEffect(() => {
    setTf('intraday')
    setBars([])
    setErr(null)
    setNote('loading live session…')
    setUpdatedAt(null)
  }, [instrumentId])

  // Tab switch (and first mount): fetch bars for the active timeframe.
  useEffect(() => {
    void loadTf(tf)
  }, [tf, loadTf])

  // LIVE graph: poll fresh intraday bars while the page stays open.
  useEffect(() => {
    if (tf !== 'intraday') return
    const iv = setInterval(() => {
      if (document.visibilityState === 'visible') void loadTf('intraday', true)
    }, INTRADAY_POLL_MS)
    return () => clearInterval(iv)
  }, [tf, loadTf])

  // Coming back to the tab: refresh immediately instead of waiting a minute.
  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === 'visible' && tf === 'intraday') void loadTf('intraday', true)
    }
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [tf, loadTf])

  const points = useMemo(() => toPoints(bars), [bars])

  useEffect(() => {
    if (!ref.current) return
    if (points.length < 2) return
    const chrome = chartChrome()
    const chart = createChart(ref.current, {
      height: 380,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: chrome.text,
        fontFamily: chrome.font,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: chrome.grid },
        horzLines: { color: chrome.grid },
      },
      rightPriceScale: { borderColor: chrome.border },
      timeScale: {
        borderColor: chrome.border,
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
    const sc = seriesColors(rising)
    const series = chart.addSeries(AreaSeries, {
      lineColor: sc.line,
      topColor: sc.top,
      bottomColor: sc.bottom,
      lineWidth: 2,
      priceLineVisible: false,
    })
    series.setData(points)
    chart.timeScale().fitContent()
    clampZoomToData(chart, points.length)

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [points, tf])

  const live = tf === 'intraday'

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
        {live ? (
          <span className="chip pos" title="Graph refreshes automatically every minute while this page is open">
            <span className="live-dot" /> LIVE · auto-updates
          </span>
        ) : null}
        <span className="faint" style={{ fontSize: 11.5 }}>
          {loading ? 'loading…' : note}
          {updatedAt ? ` · updated ${updatedAt.toLocaleTimeString()}` : ''}
        </span>
        <button
          className="btn ghost"
          style={{ padding: '2px 10px', fontSize: 12 }}
          onClick={() => void loadTf(tf)}
          aria-label="Refresh chart now"
        >
          ↻
        </button>
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
