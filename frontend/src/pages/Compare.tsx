import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { createChart, ColorType, LineSeries } from 'lightweight-charts'
import { GitCompare, Plus, Search, X } from 'lucide-react'
import { api } from '../api'
import { VerdictChip } from '../components/Verdict'
import type { Analysis, AssetDetail, Instrument } from '../types'

const COLORS = ['#22d3ee', '#8b5cf6', '#fbbf24', '#34d399']

export function ComparePage() {
  const [params, setParams] = useSearchParams()
  const ids = (params.get('ids') ?? 'sp500,nifty50').split(',').filter(Boolean).slice(0, 4)
  const [showPick, setShowPick] = useState(false)

  const details = useMultiDetails(ids)
  const analyses = useMultiAnalyses(ids)

  const normalized = useMemo(() => {
    const map: Record<string, { time: string; value: number }[]> = {}
    for (const d of details) {
      if (!d?.rows.length) continue
      const base = d.rows[0].close || 1
      map[d.instrument.id] = d.rows
        .filter((r) => r.close != null)
        .map((r) => ({ time: r.date, value: ((r.close as number) / base) * 100 }))
    }
    return map
  }, [details])

  const add = (inst: Instrument) => {
    if (!ids.includes(inst.id) && ids.length < 4) {
      setParams({ ids: [...ids, inst.id].join(',') })
    }
    setShowPick(false)
  }

  return (
    <div>
      <h1 className="page-title">Compare assets</h1>
      <p className="page-sub">
        Normalized performance (all series start at 100) with side-by-side regime verdicts. Compare an Indian index
        against the S&P 500, or a stock against its market — the math does the rest.
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {ids.map((id, i) => {
          const d = details.find((x) => x?.instrument.id === id)
          return (
            <span key={id} className="chip" style={{ fontSize: 13, padding: '6px 12px', borderColor: COLORS[i % 4] + '66' }}>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: COLORS[i % 4], display: 'inline-block', marginRight: 6 }} />
              {d?.instrument.name ?? id}
              <button
                aria-label={`Remove ${id}`}
                onClick={() => setParams({ ids: ids.filter((x) => x !== id).join(',') || 'sp500' })}
                style={{ background: 'none', border: 'none', color: 'var(--text-faint)', padding: 0, marginLeft: 6 }}
              ><X size={12} /></button>
            </span>
          )
        })}
        {ids.length < 4 ? (
          <button className="btn ghost" style={{ padding: '5px 12px' }} onClick={() => setShowPick(!showPick)}>
            <Plus size={13} /> Add asset
          </button>
        ) : null}
      </div>

      {showPick ? <AssetPicker onPick={add} /> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title"><GitCompare size={15} /> Normalized performance — 100 = period start</div>
        <CompareChart series={normalized} colors={COLORS} />
        <p className="faint">Percent moves over the last ~180 trading days, so very different price levels become comparable.</p>
      </div>

      <div className="grid cols-2">
        {ids.map((id) => {
          const a = analyses.find((x) => x?.instrument.id === id)
          return (
            <div className="card" key={id}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <b>{a?.instrument.name ?? id}</b>
                <VerdictChip verdict={a?.assessment.verdict} score={a?.assessment.score_0_100} />
                <span className="faint" style={{ marginLeft: 'auto' }}>confidence {a?.assessment.confidence ?? '—'}%</span>
              </div>
              {a?.assessment.equation ? <div className="equation">{a.assessment.equation}</div> : <p className="muted" style={{ fontSize: 13 }}>analysis loading…</p>}
              <div className="faint" style={{ marginTop: 8 }}>
                Would change if: {a?.assessment.what_would_change_this_read?.[0] ?? '…'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AssetPicker({ onPick }: { onPick: (inst: Instrument) => void }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Instrument[]>([])
  useEffect(() => {
    const t = setTimeout(async () => {
      if (!q.trim()) {
        setResults([])
        return
      }
      try {
        const res = await api.search(q)
        setResults(res.results)
      } catch {
        setResults([])
      }
    }, 180)
    return () => clearTimeout(t)
  }, [q])

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ position: 'relative' }}>
        <Search size={15} style={{ position: 'absolute', left: 12, top: 13, color: 'var(--text-faint)' }} />
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search to add — e.g. tesla, sensex, gold…"
          className="search-input"
          style={{ paddingLeft: 38, fontSize: 14, padding: '10px 12px 10px 38px' }}
        />
      </div>
      {results.length ? (
        <div style={{ marginTop: 10 }}>
          {results.map((r) => (
            <button
              key={r.id}
              className="search-item"
              style={{ width: '100%', border: 'none', background: 'transparent', color: 'var(--text)', textAlign: 'left' }}
              onClick={() => onPick(r)}
            >
              <span style={{ fontWeight: 600, fontSize: 13.5 }}>{r.name}</span>
              <span className="chip">{r.category}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function CompareChart({ series, colors }: { series: Record<string, { time: string; value: number }[]>; colors: string[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = createChart(ref.current, {
      height: 340,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#93a0b8',
        attributionLogo: false,
      },
      grid: { vertLines: { color: 'rgba(147,160,184,0.08)' }, horzLines: { color: 'rgba(147,160,184,0.08)' } },
      timeScale: { borderColor: 'rgba(147,160,184,0.15)' },
      rightPriceScale: { borderColor: 'rgba(147,160,184,0.15)' },
    })
    Object.values(series).forEach((points, i) => {
      const s = chart.addSeries(LineSeries, {
        color: colors[i % colors.length],
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      })
      s.setData(points)
    })
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [series, colors])
  return <div ref={ref} style={{ width: '100%' }} />
}

function useMultiDetails(ids: string[]): (AssetDetail | null)[] {
  const [details, setDetails] = useState<(AssetDetail | null)[]>([])
  const key = ids.join(',')
  useEffect(() => {
    let alive = true
    Promise.all(key.split(',').filter(Boolean).map((id) => api.asset(id).catch(() => null))).then((ds) => {
      if (alive) setDetails(ds)
    })
    return () => {
      alive = false
    }
  }, [key])
  return details
}

function useMultiAnalyses(ids: string[]): (Analysis | null)[] {
  const [analyses, setAnalyses] = useState<(Analysis | null)[]>([])
  const key = ids.join(',')
  useEffect(() => {
    let alive = true
    Promise.all(key.split(',').filter(Boolean).map((id) => api.analysis(id).catch(() => null))).then((as) => {
      if (alive) setAnalyses(as)
    })
    return () => {
      alive = false
    }
  }, [key])
  return analyses
}
