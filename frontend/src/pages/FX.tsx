import { Coins, Sparkles } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { CurrencyPanel } from '../components/CurrencyPanel'
import { CardSkeleton } from '../components/Skeletons'
import type { FXData } from '../types'

export function FXPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { data, loading, error } = useApi<FXData>('/api/fx?base=USD')

  return (
    <div>
      <h1 className="page-title">Currency Exchange</h1>
      <p className="page-sub">
        Pick your base currency — see it against every other major currency, convert amounts, and understand why
        these numbers matter. Rates are official ECB reference data (live) or clearly-labeled demo data.
      </p>
      {error ? <div className="err-box">{error}</div> : null}
      {loading && !data ? <CardSkeleton height={340} /> : null}
      {data ? (
        <>
          <CurrencyPanel fx={data} onExplain={onExplain} />
          <div className="grid cols-3" style={{ marginTop: 16 }}>
            {Object.entries(data.pairs).map(([pid, p]) => (
              <PairCard key={pid} pair={p} onExplain={onExplain} />
            ))}
          </div>
        </>
      ) : null}
      <p className="faint" style={{ textAlign: 'center', marginTop: 24 }}>{data?.disclaimer}</p>
    </div>
  )
}

function PairCard({ pair, onExplain }: { pair: FXData['pairs'][string]; onExplain: (t: string) => void }) {
  const up = pair.d1_pct >= 0
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <b>{pair.name}</b>
        {pair.demo ? <span className="chip demo">DEMO</span> : null}
      </div>
      <div className="num" style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>{pair.rate_usd.toFixed(4)}</div>
      <div className="num" style={{ fontSize: 13, fontWeight: 700, color: up ? 'var(--pos)' : 'var(--neg)' }}>
        {up ? '▲' : '▼'} {Math.abs(pair.d1_pct).toFixed(2)}% today · {pair.d5_pct >= 0 ? '+' : ''}{pair.d5_pct.toFixed(2)}% 5d
      </div>
      <button
        className="btn ghost"
        style={{ fontSize: 12, marginTop: 10, padding: '5px 10px' }}
        onClick={() =>
          onExplain(
            `${pair.name} is at ${pair.rate_usd.toFixed(4)}, which moved ${pair.d5_pct >= 0 ? '+' : ''}${pair.d5_pct.toFixed(2)}% over 5 days and ${pair.d1_pct >= 0 ? '+' : ''}${pair.d1_pct.toFixed(2)}% today. In simple words: this tells you how much of the quoted currency one unit of the base currency buys, and whether that exchange value is rising or falling — it affects import prices, travel costs and export competitiveness.`,
          )
        }
      >
        <Sparkles size={12} /> What does this mean? (PA)
      </button>
      <div style={{ display: 'none' }}><Coins size={1} /></div>
    </div>
  )
}
