import { Link, useParams } from 'react-router-dom'
import { GitCompare, ArrowLeft, Sparkles, Sigma, Clock } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useWatchlist } from '../hooks/useWatchlist'
import { RegimeGauge } from '../components/Verdict'
import { EvidencePanel } from '../components/Evidence'
import { FilterReadout } from '../components/FilterReadout'
import { ThesisCard } from '../components/ThesisCard'
import { PriceChart } from '../components/PriceChart'
import { NewsList } from '../components/NewsList'
import { ImageAnalyzer } from '../components/ImageAnalyzer'
import { LoadingProgress } from '../components/LoadingProgress'
import { OutlookCard } from '../components/OutlookCard'
import { TimeframeStats } from '../components/TimeframeStats'
import { CardSkeleton } from '../components/Skeletons'
import { ErrorBoundary } from '../components/ErrorBoundary'
import type { Analysis, AssetDetail } from '../types'

function AnalysisMethodChip({ analysis }: { analysis?: Analysis | null }) {
  if (!analysis?.thesis) return null
  const by = analysis.thesis.generated_by
  const label =
    by === 'gemini-analysis' ? '✨ AI thesis — Gemini, from the math below'
      : by === 'deterministic-template' ? ' Thesis — deterministic template (AI off)'
        : by === 'unavailable' ? ' Thesis — AI needs a Gemini key'
          : ` Thesis — ${by}`
  return (
    <span className="chip" title="How this explanation was produced">
      <Sparkles size={11} /> {label}
    </span>
  )
}

export function AssetDetailPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { id = '' } = useParams()
  const detail = useApi<AssetDetail>(`/api/asset/${id}`)
  const analysis = useApi<Analysis>(`/api/analysis/${id}`)
  const watchlist = useWatchlist()

  if (detail.error) {
    return (
      <div className="err-box" style={{ marginTop: 30 }}>
        <span>Couldn't load this asset: {detail.error}</span>
        <Link className="btn" to="/">← Back to overview</Link>
      </div>
    )
  }
  if (!detail.data) return <CardSkeleton height={420} />

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
        <AnalysisMethodChip analysis={a} />
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
        {d.delayed_live ? (
          <span
            className="chip"
            title={d.delayed_live.note}
            style={{ display: 'inline-flex', alignItems: 'baseline', gap: 6 }}
          >
            <span className="live-dot" />
            ≈ live ₹{d.delayed_live.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            <span style={{ color: d.delayed_live.change_pct >= 0 ? 'var(--pos)' : 'var(--neg)', fontWeight: 700 }}>
              {d.delayed_live.change_pct >= 0 ? '▲' : '▼'} {Math.abs(d.delayed_live.change_pct).toFixed(2)}%
            </span>
            <span className="muted" style={{ fontSize: 11 }}>· 15-min delayed</span>
          </span>
        ) : null}
      </div>

      {/* Chart loads immediately from the lightweight asset endpoint */}
      <section className="section">
        <div className="card">
          <ErrorBoundary name="PriceChart">
            {d.rows.length ? (
              <PriceChart
                initialBars={d.rows.map((r) => ({ time: r.date, close: r.close }))}
                instrumentId={d.instrument.id}
              />
            ) : (
              <p className="muted">No chart data.</p>
            )}
          </ErrorBoundary>
        </div>
      </section>

      {/* Intraday · Daily · Monthly bullish/bearish stats */}
      <section className="section">
        <h2 className="card-title" style={{ fontSize: 15 }}>
          <Clock size={15} /> Timeframe signals — intraday, daily & monthly
        </h2>
        <ErrorBoundary name="TimeframeStats">
          <TimeframeStats instrumentId={id} />
        </ErrorBoundary>
      </section>

      {/* Live progress: stage + time remaining for the deep analysis */}
      <LoadingProgress instrumentId={id} loading={analysis.loading && !analysis.data} />

      {/* Clear outlook — the instant plain-English answer */}
      {a?.outlook ? (
        <section className="section">
          <OutlookCard outlook={a.outlook} verdict={a.assessment?.verdict} />
        </section>
      ) : null}

      {/* Verdict — always visible; appears as soon as analysis lands */}
      <section className="grid cols-2" style={{ alignItems: 'stretch' }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div className="card-title"><Sigma size={15} /> Regime verdict</div>
          {a?.assessment ? (
            <RegimeGauge
              verdict={a.assessment.verdict}
              score={a.assessment.score_0_100}
              confidence={a.assessment.confidence}
              equation={a.assessment.equation}
            />
          ) : (
            <div style={{ padding: '20px 0' }}>
              <CardSkeleton height={130} />
              <p className="faint" style={{ textAlign: 'center', marginTop: 10 }}>
                {analysis.loading ? 'Scoring the regime — fetching drivers, news and math…' : 'Assessment unavailable.'}
              </p>
            </div>
          )}
        </div>
        <div>
          {a?.assessment ? (
            <EvidencePanel assessment={a.assessment} />
          ) : (
            <div className="card">
              <div className="card-title">Why this verdict — the evidence</div>
              <CardSkeleton height={200} />
              <p className="faint" style={{ marginTop: 8 }}>
                The factor table (every input, rule, weight and contribution) appears here the moment scoring completes.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* AI thesis — always visible, right under the evidence */}
      <section className="section">
        {a?.thesis ? (
          <ThesisCard thesis={a.thesis} onExplain={onExplain} equation={a.assessment?.equation} />
        ) : (
          <div className="card">
            <div className="card-title"><Sparkles size={15} /> Analyst thesis</div>
            <CardSkeleton height={110} />
            <p className="faint" style={{ marginTop: 8 }}>The AI translation of the math above — loading…</p>
          </div>
        )}
      </section>

      {/* Deterministic filters */}
      <section className="section">
        <h2 className="card-title" style={{ fontSize: 15 }}>Deterministic filters — computed before any AI</h2>
        {a ? <FilterReadout filters={a.filters} cross={a.cross_asset} /> : <CardSkeleton height={160} />}
      </section>

      <section className="grid cols-2" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="card-title">
            Related news
            {a?.news ? (
              <span className={`chip ${a.news.aggregate_score > 0.1 ? 'pos' : a.news.aggregate_score < -0.1 ? 'neg' : 'neutral'}`}>
                tone {a.news.aggregate_score >= 0 ? '+' : ''}{a.news.aggregate_score.toFixed(2)} · {a.news.method === 'gemini' ? 'AI-tagged' : a.news.method}
              </span>
            ) : null}
          </div>
          {a ? <NewsList articles={a.news.articles} /> : <CardSkeleton height={180} />}
        </div>
        <ImageAnalyzer />
      </section>

      <p className="faint" style={{ textAlign: 'center', marginTop: 26 }}>{d.disclaimer}</p>
    </div>
  )
}
