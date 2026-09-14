import { Link, useParams } from 'react-router-dom'
import { GitCompare, ArrowLeft } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useWatchlist } from '../hooks/useWatchlist'
import { RegimeGauge } from '../components/Verdict'
import { EvidencePanel } from '../components/Evidence'
import { FilterReadout } from '../components/FilterReadout'
import { ThesisCard } from '../components/ThesisCard'
import { PriceChart } from '../components/PriceChart'
import { NewsList } from '../components/NewsList'
import { ImageAnalyzer } from '../components/ImageAnalyzer'
import { PageSkeleton } from '../components/Skeletons'
import type { Analysis, AssetDetail } from '../types'
import { useState } from 'react'

export function AssetDetailPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { id = '' } = useParams()
  const detail = useApi<AssetDetail>(`/api/asset/${id}`)
  const analysis = useApi<Analysis>(`/api/analysis/${id}`)
  const watchlist = useWatchlist()
  const [tab, setTab] = useState<'evidence' | 'thesis'>('evidence')

  if (detail.error) {
    return (
      <div className="err-box" style={{ marginTop: 30 }}>
        <span>Couldn't load this asset: {detail.error}</span>
        <Link className="btn" to="/">← Back to overview</Link>
      </div>
    )
  }
  if (!detail.data) return <PageSkeleton />

  const d = detail.data
  const a = analysis.data
  const up = (d.quote?.change_pct ?? 0) >= 0

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 24, flexWrap: 'wrap' }}>
        <Link to="/" className="btn ghost" style={{ padding: '6px 10px' }}><ArrowLeft size={14} /> Overview</Link>
        <Link to={`/compare?ids=${id}`} className="btn ghost" style={{ padding: '6px 10px' }}><GitCompare size={14} /> Compare</Link>
        <button className="btn ghost" style={{ padding: '6px 10px' }} onClick={() => watchlist.toggle(d.instrument.id)}>
          {watchlist.has(d.instrument.id) ? '★ Watching' : '☆ Watch'}
        </button>
        {d.data_mode === 'demo' ? <span className="chip demo">DEMO DATA</span> : <span className="chip pos">live · via {d.quote?.provider}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap', marginTop: 10 }}>
        <h1 className="page-title" style={{ margin: 0 }}>{d.instrument.name}</h1>
        <span className="chip">{d.instrument.category} · {d.instrument.region}</span>
        {d.quote ? (
          <span style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span className="num" style={{ fontSize: 30, fontWeight: 800 }}>
              {d.quote.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
            <span className="num" style={{ fontSize: 16, fontWeight: 700, color: up ? 'var(--pos)' : 'var(--neg)' }}>
              {up ? '▲' : '▼'} {Math.abs(d.quote.change_pct).toFixed(2)}%
            </span>
          </span>
        ) : null}
      </div>

      <section className="section">
        <div className="card">{d.rows.length ? <PriceChart data={d} /> : <p className="muted">No chart data.</p>}</div>
      </section>

      <section className="grid cols-2" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="card-title">Regime assessment</div>
          {a?.assessment ? (
            <RegimeGauge
              verdict={a.assessment.verdict}
              score={a.assessment.score_0_100}
              confidence={a.assessment.confidence}
              equation={a.assessment.equation}
            />
          ) : (
            <p className="muted">{analysis.loading ? 'Scoring the regime…' : 'Assessment unavailable.'}</p>
          )}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
            <button className={`btn ${tab === 'evidence' ? 'primary' : 'ghost'}`} style={{ fontSize: 12.5 }} onClick={() => setTab('evidence')}>Evidence</button>
            <button className={`btn ${tab === 'thesis' ? 'primary' : 'ghost'}`} style={{ fontSize: 12.5 }} onClick={() => setTab('thesis')}>AI thesis</button>
          </div>
        </div>
        <div>
          {tab === 'evidence' ? (
            a?.assessment ? <EvidencePanel assessment={a.assessment} /> : <div className="card muted">Loading evidence…</div>
          ) : a?.thesis ? (
            <ThesisCard thesis={a.thesis} onExplain={onExplain} />
          ) : (
            <div className="card muted">{analysis.loading ? 'Composing thesis…' : 'Thesis unavailable.'}</div>
          )}
        </div>
      </section>

      <section className="section">
        <h2 className="card-title" style={{ fontSize: 15 }}>Deterministic filters — computed before any AI</h2>
        {a ? <FilterReadout filters={a.filters} cross={a.cross_asset} /> : <div className="card muted">Loading filters…</div>}
      </section>

      <section className="grid cols-2" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="card-title">Related news {a?.news ? <span className={`chip ${a.news.aggregate_score > 0.1 ? 'pos' : a.news.aggregate_score < -0.1 ? 'neg' : 'neutral'}`}>tone {a.news.aggregate_score >= 0 ? '+' : ''}{a.news.aggregate_score.toFixed(2)} · {a.news.method}</span> : null}</div>
          {a ? <NewsList articles={a.news.articles} /> : <p className="muted">Loading news…</p>}
        </div>
        <ImageAnalyzer />
      </section>

      <p className="faint" style={{ textAlign: 'center', marginTop: 26 }}>{d.disclaimer}</p>
    </div>
  )
}
