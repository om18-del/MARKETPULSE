import { Link } from 'react-router-dom'
import type { Overview } from '../types'

function cellColor(pct: number): string {
  const clamped = Math.max(-3, Math.min(3, pct))
  const alpha = 0.12 + (Math.abs(clamped) / 3) * 0.55
  return clamped >= 0
    ? `color-mix(in srgb, var(--pos) ${Math.round(alpha * 100)}%, transparent)`
    : `color-mix(in srgb, var(--neg) ${Math.round(alpha * 100)}%, transparent)`
}

export function Heatmap({ data }: { data: Overview['heatmap'] }) {
  if (!data?.length) return null
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(104px, 1fr))', gap: 8 }}>
      {data.map((h) => (
        <Link to={`/asset/${h.id}`} key={h.id} className="heat-cell" style={{ background: cellColor(h.change_pct) }}>
          <div className="heat-name" title={h.name}>{h.name}</div>
          <div className="heat-pct num" style={{ color: h.change_pct >= 0 ? 'var(--pos)' : 'var(--neg)' }}>
            {h.change_pct >= 0 ? '+' : ''}{h.change_pct.toFixed(2)}%
          </div>
        </Link>
      ))}
    </div>
  )
}
