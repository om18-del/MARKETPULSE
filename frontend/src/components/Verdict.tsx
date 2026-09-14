import { motion } from 'framer-motion'
import type { Verdict as V } from '../types'

const VERDICT_COLOR: Record<string, string> = {
  bullish: 'var(--pos)',
  bearish: 'var(--neg)',
  neutral: 'var(--neutral)',
  uncertain: 'var(--uncertain)',
}

export function VerdictChip({ verdict, score }: { verdict?: V; score?: number }) {
  if (!verdict) return <span className="chip">n/a</span>
  return (
    <span className={`chip ${verdict} bg-${verdict}`} style={{ textTransform: 'capitalize' }}>
      {verdict}{score !== undefined ? ` · ${Math.round(score)}` : ''}
    </span>
  )
}

export function RegimeGauge({
  verdict,
  score,
  confidence,
  equation,
}: {
  verdict?: V
  score?: number
  confidence?: number
  equation?: string
}) {
  const s = score ?? 50
  const color = VERDICT_COLOR[verdict ?? 'neutral'] ?? 'var(--neutral)'
  // semicircle gauge 0..100
  const R = 84
  const cx = 100
  const cy = 96
  const angle = Math.PI * (1 - s / 100)
  const nx = cx + R * Math.cos(angle)
  const ny = cy - R * Math.sin(angle)
  return (
    <div className="gauge-wrap">
      <svg width="200" height="118" viewBox="0 0 200 118" role="img" aria-label={`Regime ${verdict} ${s} of 100`}>
        <path d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`} fill="none" stroke="var(--card-hover)" strokeWidth="13" strokeLinecap="round" />
        <motion.path
          d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth="13"
          strokeLinecap="round"
          strokeDasharray={Math.PI * R}
          initial={{ strokeDashoffset: Math.PI * R }}
          animate={{ strokeDashoffset: Math.PI * R * (1 - s / 100) }}
          transition={{ type: 'spring', stiffness: 40, damping: 16 }}
        />
        <motion.line
          x1={cx} y1={cy}
          x2={nx} y2={ny}
          stroke="var(--text)"
          strokeWidth="3"
          strokeLinecap="round"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, x2: nx, y2: ny }}
          transition={{ type: 'spring', stiffness: 40, damping: 16 }}
        />
        <circle cx={cx} cy={cy} r="5" fill="var(--text)" />
      </svg>
      <motion.div
        className={`gauge-value num v-${verdict ?? 'neutral'}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {Math.round(s)}<span style={{ fontSize: 18, color: 'var(--text-faint)' }}> /100</span>
      </motion.div>
      <div className={`chip ${verdict ?? 'neutral'} bg-${verdict ?? 'neutral'}`} style={{ fontSize: 14, padding: '5px 16px', textTransform: 'capitalize' }}>
        {verdict ?? '…'}
        {confidence !== undefined ? ` · ${confidence}% confidence` : ''}
      </div>
      {equation ? <div className="equation" style={{ marginTop: 10, maxWidth: 560 }}>{equation}</div> : null}
    </div>
  )
}
