import { useEffect, useRef } from 'react'
import { createChart, ColorType, AreaSeries, type IChartApi } from 'lightweight-charts'
import type { AssetDetail } from '../types'

/**
 * Build strictly-ascending, unique-timestamp points for lightweight-charts.
 * The library hard-throws on duplicate/unordered times, which previously
 * unmounted the whole page — so we guarantee the invariants here and drop
 * any bar whose timestamp is not strictly newer than the previous one.
 */
function toChartPoints(data: AssetDetail): { time: string; value: number }[] {
  const rows = [...(data.rows ?? [])]
    .filter((r) => r.close != null && r.date)
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
  const points: { time: string; value: number }[] = []
  let prev = ''
  for (const r of rows) {
    if (r.date <= prev) continue // duplicate or out-of-order timestamp
    points.push({ time: r.date, value: r.close as number })
    prev = r.date
  }
  return points
}

export function PriceChart({ data }: { data: AssetDetail }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const points = toChartPoints(data)

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
      timeScale: { borderColor: 'rgba(147,160,184,0.15)', visible: true },
      crosshair: { mode: 0 },
      // ResizeObserver-driven sizing: avoids measuring a 0-width container
      // during layout (which produced SVG <line> warnings on first paint).
      autoSize: true,
    })
    chartRef.current = chart

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#22d3ee',
      topColor: 'rgba(34,211,238,0.30)',
      bottomColor: 'rgba(34,211,238,0.0)',
      lineWidth: 2,
      priceLineVisible: false,
    })
    series.setData(points)
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  if (points.length < 2) {
    return <p className="muted">Not enough history yet to draw a chart.</p>
  }

  return <div ref={ref} style={{ width: '100%' }} />
}
