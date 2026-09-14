import { useState } from 'react'
import { ChevronDown, Scale, ShieldQuestion, Sigma } from 'lucide-react'
import type { Assessment } from '../types'

function ContribBar({ sub, weight }: { sub: number; weight: number }) {
  const pct = Math.min(100, Math.abs(sub) * 100)
  const positive = sub >= 0
  return (
    <div className="factor-bar" title={`contribution ${(sub * weight).toFixed(3)}`}>
      <div style={{ width: `${pct}%`, background: positive ? 'var(--pos)' : 'var(--neg)' }} />
    </div>
  )
}

function FactorGroup({ title, score, weight, parts, defaultOpen = false }: {
  title: string
  score: number
  weight: number
  parts: { name: string; value: string; rule: string; weight: number; sub_score: number; meaning: string }[]
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginBottom: 8 }}>
      <button
        onClick={() => setOpen(!open)}
        className="card"
        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', cursor: 'pointer' }}
      >
        <span style={{ fontWeight: 700, fontSize: 13.5, flex: 1, textAlign: 'left' }}>{title}</span>
        <span className="faint num">weight {(weight * 100).toFixed(0)}%</span>
        <span
          className="num"
          style={{ fontWeight: 700, color: score >= 0 ? 'var(--pos)' : 'var(--neg)', fontSize: 13 }}
        >
          {score >= 0 ? '+' : ''}{score.toFixed(2)}
        </span>
        <ChevronDown size={15} style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
      </button>
      {open ? (
        <div style={{ padding: '8px 4px' }}>
          <div className="factor-row faint" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <span>Factor</span><span>Value</span><span>Rule / meaning</span><span>Contribution</span>
          </div>
          {parts.map((p, i) => (
            <div className="factor-row" key={i}>
              <span className="factor-name">{p.name}</span>
              <span className="num">{p.value}</span>
              <span>
                <span className="factor-rule" style={{ display: 'block' }}>{p.rule}</span>
                <span className="faint">{p.meaning}</span>
              </span>
              <ContribBar sub={p.sub_score} weight={p.weight} />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function EvidencePanel({ assessment }: { assessment: Assessment }) {
  const [tab, setTab] = useState<'factors' | 'flip'>('factors')
  if (!assessment.available) {
    return <div className="card muted">Insufficient data for evidence breakdown.</div>
  }
  const f = assessment.factors
  return (
    <div className="card">
      <div className="card-title">
        <Scale size={15} /> Why this verdict — the evidence
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        <button className={`btn ${tab === 'factors' ? 'primary' : 'ghost'}`} onClick={() => setTab('factors')} style={{ padding: '7px 14px' }}>
          Factor table
        </button>
        <button className={`btn ${tab === 'flip' ? 'primary' : 'ghost'}`} onClick={() => setTab('flip')} style={{ padding: '7px 14px' }}>
          What would change this read
        </button>
      </div>

      {tab === 'factors' && f ? (
        <div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
            <span className="chip"><Sigma size={12} /> {assessment.equation ? 'score equation below' : ''}</span>
          </div>
          <FactorGroup title="Trend" score={f.trend.score} weight={assessment.weights?.trend ?? 0.35} parts={f.trend.parts} defaultOpen />
          <FactorGroup title="Momentum" score={f.momentum.score} weight={assessment.weights?.momentum ?? 0.25} parts={f.momentum.parts} />
          <FactorGroup title="Volatility" score={f.volatility.score} weight={assessment.weights?.volatility ?? 0.25} parts={f.volatility.parts} />
          <FactorGroup title="Volume" score={f.volume.score} weight={assessment.weights?.volume ?? 0.15} parts={f.volume.parts} />
          <div className="factor-row" style={{ marginTop: 6 }}>
            <span className="factor-name">News modifier</span>
            <span className="num">{f.news.score >= 0 ? '+' : ''}{f.news.score.toFixed(3)}</span>
            <span className="factor-rule">{f.news.meaning}</span>
            <span className="faint">cap ±{( (assessment.weights?.news_cap ?? 0.1) * 100).toFixed(0)}%</span>
          </div>
          {assessment.equation ? <div className="equation" style={{ marginTop: 12 }}>{assessment.equation}</div> : null}
        </div>
      ) : (
        <div>
          {assessment.what_would_change_this_read?.map((w, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, padding: '9px 0', borderBottom: '1px solid var(--card-border)' }}>
              <ShieldQuestion size={16} style={{ color: 'var(--accent-a)', flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: 13.5 }}>{w}</span>
            </div>
          ))}
          <p className="faint" style={{ marginTop: 12 }}>
            Verdicts describe the current environment — never the future. This list shows exactly which
            observed conditions would flip the read.
          </p>
        </div>
      )}
    </div>
  )
}
