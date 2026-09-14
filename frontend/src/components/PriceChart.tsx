import { useEffect, useRef } from 'react'
import { createChart, ColorType, AreaSeries, type IChartApi } from 'lightweight-charts'
import type { AssetDetail } from '../types'

export function PriceChart({ data }: { data: AssetDetail }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!ref.current) return
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
      autoSize: false,
    })
    chartRef.current = chart

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#22d3ee',
      topColor: 'rgba(34,211,238,0.30)',
      bottomColor: 'rgba(34,211,238,0.0)',
      lineWidth: 2,
      priceLineVisible: false,
    })
    const points = data.rows
      .filter((r) => r.close != null)
      .map((r) => ({ time: r.date, value: r.close as number }))
    series.setData(points)
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [data])

  return <div ref={ref} style={{ width: '100%' }} />
}
