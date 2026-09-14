import { useApi } from '../hooks/useApi'
import { CardSkeleton } from '../components/Skeletons'
import type { Methodology as MethodologyData } from '../types'

export function MethodologyPage() {
  const { data, loading, error } = useApi<MethodologyData>('/api/methodology')

  return (
    <div>
      <h1 className="page-title">Methodology & Research</h1>
      <p className="page-sub">Exactly how every verdict is produced — indicators, origins, rules and weights. Fully auditable.</p>

      {error ? <div className="err-box">{error}</div> : null}
      {loading && !data ? <CardSkeleton height={320} /> : null}

      {data ? (
        <>
          <div className="card">
            <div className="card-title">Philosophy</div>
            {data.philosophy.map((p, i) => (
              <p key={i} style={{ fontSize: 14, margin: '8px 0', color: 'var(--text-dim)' }}>• {p}</p>
            ))}
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-title">The regime model</div>
            <p style={{ fontSize: 14 }}>{data.regime_model.description}</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10, margin: '14px 0' }}>
              {Object.entries(data.regime_model.weights).map(([k, v]) => (
                <div key={k} className="card" style={{ padding: '10px 13px', textAlign: 'center' }}>
                  <div className="num" style={{ fontSize: 21, fontWeight: 800, color: 'var(--accent-a)' }}>
                    {typeof v === 'number' ? `${(v * 100).toFixed(0)}%` : v}
                  </div>
                  <div className="faint" style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
            <p style={{ fontSize: 13.5, color: 'var(--text-dim)' }}><b>Why these weights:</b> {data.regime_model.why_these_weights}</p>
            <div className="equation">{Object.entries(data.regime_model.verdict_mapping).map(([k, v]) => `${k}: ${v}`).join('\n')}</div>
            <p style={{ fontSize: 13.5, color: 'var(--text-dim)', marginTop: 10 }}><b>Confidence:</b> {data.regime_model.confidence}</p>
            <p className="faint">Scale: {data.regime_model.scale}</p>
          </div>

          <h2 className="card-title" style={{ fontSize: 15, marginTop: 24 }}>Every indicator: origin, purpose, in-app rule</h2>
          {data.indicators.map((ind) => (
            <div className="card" key={ind.name} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <b style={{ fontSize: 14.5 }}>{ind.name}</b>
                <span className="chip" style={{ marginLeft: 'auto' }}>{ind.origin}</span>
              </div>
              <p style={{ fontSize: 13.5, margin: '8px 0 4px' }}><b>What:</b> {ind.what}</p>
              <p style={{ fontSize: 13.5, margin: '4px 0', color: 'var(--text-dim)' }}><b>Why it's used:</b> {ind.why}</p>
              {ind.rule_in_app ? <p className="faint" style={{ margin: '4px 0 0' }}><b>Rule in MarketPulse:</b> {ind.rule_in_app}</p> : null}
            </div>
          ))}

          <div className="card" style={{ marginTop: 16, borderColor: 'color-mix(in srgb, var(--neutral) 30%, transparent)' }}>
            <div className="card-title">Honesty notes</div>
            {data.honesty_notes.map((h, i) => (
              <p key={i} style={{ fontSize: 13.5, margin: '8px 0', color: 'var(--text-dim)' }}>• {h}</p>
            ))}
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-title">The two AI roles</div>
            <p style={{ fontSize: 13.5 }}><b>Analysis Engine:</b> {data.ai_separation.analysis_engine}</p>
            <p style={{ fontSize: 13.5 }}><b>Pulse Assistant:</b> {data.ai_separation.pulse_assistant}</p>
            <p className="faint">{data.ai_separation.shared_rule}</p>
          </div>
        </>
      ) : null}
    </div>
  )
}
