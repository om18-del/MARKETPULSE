import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Star } from 'lucide-react'
import type { GridEntry } from '../types'
import { Spark } from './Spark'
import { VerdictChip } from './Verdict'

export function IndexCard({
  e,
  index = 0,
  watched,
  onToggleWatch,
}: {
  e: GridEntry
  index?: number
  watched?: boolean
  onToggleWatch?: (id: string) => void
}) {
  const up = (e.change_pct ?? 0) >= 0
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.035, 0.5), duration: 0.35 }}
    >
      <Link to={`/asset/${e.id}`} className="card hoverable idx-card" style={{ display: 'block' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="idx-name" style={{ flex: 1 }}>{e.name}</span>
          {e.demo ? <span className="chip demo">DEMO</span> : null}
          {onToggleWatch ? (
            <button
              aria-label={watched ? 'Remove from watchlist' : 'Add to watchlist'}
              onClick={(ev) => {
                ev.preventDefault()
                ev.stopPropagation()
                onToggleWatch(e.id)
              }}
              style={{ background: 'none', border: 'none', padding: 2, color: watched ? 'var(--neutral)' : 'var(--text-faint)' }}
            >
              <Star size={15} fill={watched ? 'var(--neutral)' : 'none'} />
            </button>
          ) : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 8 }}>
          <div>
            <div className="idx-price num">{e.price?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'}</div>
            <div className="num" style={{ color: up ? 'var(--pos)' : 'var(--neg)', fontSize: 13, fontWeight: 700 }}>
              {up ? '▲' : '▼'} {Math.abs(e.change_pct ?? 0).toFixed(2)}%
            </div>
          </div>
          <Spark points={e.spark ?? []} />
        </div>
        <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <VerdictChip verdict={e.verdict} score={e.score} />
          <span className="faint">{e.currency}</span>
        </div>
      </Link>
    </motion.div>
  )
}
