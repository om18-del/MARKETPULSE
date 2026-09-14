import { useMemo, useState } from 'react'
import { ArrowLeftRight, Coins, Sparkles } from 'lucide-react'
import type { FXData } from '../types'
import { usePreferredCurrency } from '../hooks/usePreferredCurrency'

export function CurrencyPanel({ fx, onExplain }: { fx: FXData; onExplain?: (text: string) => void }) {
  const { currency, setCurrency } = usePreferredCurrency()
  const [amount, setAmount] = useState('100')
  const [from, setFrom] = useState('USD')
  const [to, setTo] = useState(currency)
  const [converted, setConverted] = useState<number | null>(null)

  const rates = fx.usd_rates
  const rate = useMemo(() => {
    const rf = rates[from]
    const rt = rates[to]
    if (!rf || !rt) return null
    return rt / rf
  }, [rates, from, to])

  const convert = async () => {
    const res = await fetch('/api/fx/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: Number(amount), from_currency: from, to_currency: to }),
    })
    const json = await res.json()
    setConverted(json.result)
  }

  return (
    <div className="card">
      <div className="card-title">
        <Coins size={15} /> Currency Exchange
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <label className="faint" htmlFor="base-sel">Your base</label>
          <select
            id="base-sel"
            value={currency}
            onChange={(e) => {
              setCurrency(e.target.value)
              setTo(e.target.value)
            }}
            style={{
              background: 'var(--bg-soft)', color: 'var(--text)', border: '1px solid var(--card-border)',
              borderRadius: 8, padding: '4px 8px', fontSize: 13,
            }}
          >
            {fx.currencies.map((c) => (
              <option key={c} value={c}>{fx.flags[c]} {c}</option>
            ))}
          </select>
        </span>
      </div>

      {/* converter */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputMode="decimal"
          className="num"
          style={{
            width: 110, background: 'var(--bg-soft)', color: 'var(--text)',
            border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', fontSize: 14,
          }}
        />
        <select value={from} onChange={(e) => setFrom(e.target.value)} style={selStyle}>
          {fx.currencies.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <ArrowLeftRight size={14} style={{ color: 'var(--text-faint)' }} />
        <select value={to} onChange={(e) => setTo(e.target.value)} style={selStyle}>
          {fx.currencies.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="btn primary" onClick={convert} style={{ padding: '8px 14px' }}>Convert</button>
        {converted !== null ? (
          <span className="num" style={{ fontWeight: 700, fontSize: 15 }}>
            ≈ {converted.toLocaleString()} {to}
          </span>
        ) : rate ? (
          <span className="faint num">1 {from} = {rate.toFixed(4)} {to}</span>
        ) : null}
      </div>

      {/* rate grid */}
      <div style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th />
              {fx.currencies.map((c) => (
                <th key={c} style={{ textAlign: 'right' }}>{fx.flags[c]} {c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fx.currencies.map((base) => {
              const rb = rates[base]
              return (
                <tr key={base} style={base === currency ? { background: 'var(--card)' } : undefined}>
                  <td style={{ fontWeight: 700 }}>{fx.flags[base]} {base}</td>
                  {fx.currencies.map((quote) => {
                    const rq = rates[quote]
                    const v = rb && rq ? rq / rb : null
                    return (
                      <td key={quote} className="num" style={{ textAlign: 'right', color: base === quote ? 'var(--text-faint)' : undefined }}>
                        {base === quote ? '—' : v ? v.toFixed(v > 20 ? 1 : 4) : 'n/a'}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {onExplain ? (
        <button
          className="btn ghost"
          style={{ marginTop: 12, fontSize: 12.5 }}
          onClick={() =>
            onExplain(
              `Currency rates: 1 USD = ${rates['INR']} INR, ${rates['EUR']} EUR... These rates show how much of one currency exchanges for another, and shifts affect import prices, travel and exports.`,
            )
          }
        >
          <Sparkles size={13} /> What do these rates mean? (PA)
        </button>
      ) : null}
      {fx.pairs && Object.keys(fx.pairs).length ? (
        <div className="faint" style={{ marginTop: 10 }}>
          Live pairs: {Object.values(fx.pairs).map((p) => `${p.name} ${p.rate_usd.toFixed(4)} (${p.d1_pct >= 0 ? '+' : ''}${p.d1_pct}%)`).join(' · ')}
        </div>
      ) : null}
    </div>
  )
}

const selStyle: React.CSSProperties = {
  background: 'var(--bg-soft)',
  color: 'var(--text)',
  border: '1px solid var(--card-border)',
  borderRadius: 10,
  padding: '8px 10px',
  fontSize: 13.5,
}
