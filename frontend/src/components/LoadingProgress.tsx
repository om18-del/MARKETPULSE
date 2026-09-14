import { useEffect, useState } from 'react'
import { Loader2, Timer } from 'lucide-react'
import { api } from '../api'

export interface AnalysisProgress {
  active: boolean
  done: boolean
  cached: boolean
  stage: string
  stages_done?: { stage: string; seconds: number }[]
  pct: number
  elapsed_seconds: number
  seconds_remaining: number
  estimated_total_seconds?: number
  note?: string
}

const STAGE_LABEL: Record<string, string> = {
  queued: 'Queued',
  starting: 'Starting',
  history: 'Fetching price history from providers',
  'drivers+news': 'Fetching VIX, macro drivers & news',
  filters: 'Computing deterministic filters',
  'cross-asset': 'Scoring cross-asset pressure',
  regime: 'Scoring the regime (20-indicator math)',
  thesis: 'AI writing the thesis (Gemini)',
  ready: 'Ready',
}

function fmt(sec: number): string {
  if (sec >= 90) return `${Math.round(sec / 60)} min`
  return `${Math.max(1, Math.round(sec))}s`
}

/** Live stage + time-remaining strip for the deep-analysis endpoint.
 *  Polls /api/analysis/{id}/progress while the analysis runs. */
export function LoadingProgress({ instrumentId, loading }: { instrumentId: string; loading: boolean }) {
  const [p, setP] = useState<AnalysisProgress | null>(null)

  useEffect(() => {
    if (!loading) return
    let alive = true
    const poll = async () => {
      try {
        const prog = await api.analysisProgress(instrumentId)
        if (alive) setP(prog)
      } catch {
        /* progress is best-effort */
      }
    }
    poll()
    const t = setInterval(poll, 1000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [instrumentId, loading])

  if (!loading || !p || p.done) return null
  const { pct, stage, elapsed_seconds, seconds_remaining, estimated_total_seconds: est } = p

  return (
    <div className="card" style={{ padding: '13px 16px', marginBottom: 14, borderColor: 'color-mix(in srgb, var(--accent-a) 30%, var(--card-border))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <Loader2 size={15} className="spin" style={{ color: 'var(--accent-a)', flexShrink: 0 }} />
        <b style={{ fontSize: 13.5 }}>{STAGE_LABEL[stage] ?? stage}</b>
        <span className="faint" style={{ fontSize: 12.5 }}>
          · elapsed {fmt(elapsed_seconds)}
        </span>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12.5, color: 'var(--accent-a)', fontWeight: 700 }}>
          <Timer size={13} />
          {seconds_remaining > 3 ? `~${fmt(seconds_remaining)} remaining` : 'almost done…'}
          {est && est > 20 ? <span className="faint" style={{ fontWeight: 400 }}>· total {fmt(est)}</span> : null}
          <span className="faint" style={{ fontWeight: 400 }}>· {pct}%</span>
        </span>
      </div>
      <div style={{ height: 5, borderRadius: 4, background: 'var(--card-hover)', overflow: 'hidden', marginTop: 9 }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 4,
          background: 'var(--accent-grad)', transition: 'width 0.9s ease',
        }} />
      </div>
      {p.note ? <div className="faint" style={{ fontSize: 12, marginTop: 7 }}>{p.note}</div> : null}
    </div>
  )
}
