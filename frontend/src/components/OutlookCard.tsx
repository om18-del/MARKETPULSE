import { AlertTriangle, ArrowDownRight, ArrowUpRight, Minus, Newspaper, ShieldAlert, Sigma } from 'lucide-react'

export interface Outlook {
  headline: string
  plain_summary: string
  key_drivers: { name: string; value: string; direction: 'up' | 'down' | 'flat'; meaning: string }[]
  risk_level: 'calm' | 'moderate' | 'elevated' | 'extreme' | 'unknown'
  realized_vol?: number | null
  news_influence?: { tone: string; score: number; method: string }
  watch_next?: string[]
  logic_note?: string
}

/** The "clear answer" card: deterministic plain-English outlook assembled
 *  from the same numbers shown in the Evidence panel — no black box. */
export function OutlookCard({ outlook, verdict }: { outlook?: Outlook | null; verdict?: string | null }) {
  if (!outlook) return null
  const risk = outlook.risk_level ?? 'unknown'

  return (
    <div className="card" style={{
      borderColor: 'color-mix(in srgb, var(--accent-a) 30%, var(--card-border))',
      background: 'linear-gradient(135deg, color-mix(in srgb, var(--accent-a) 5%, var(--card)), var(--card))',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Sigma size={16} style={{ color: 'var(--accent-a)' }} />
        <div className="card-title" style={{ margin: 0, border: 'none', padding: 0 }}>Clear outlook — what the math says</div>
        {verdict ? <span className={`chip ${verdict === 'bullish' ? 'pos' : verdict === 'bearish' ? 'neg' : 'neutral'}`}>{verdict}</span> : null}
        <span className="chip" style={{ marginLeft: 'auto' }}>
          <ShieldAlert size={11} /> risk: {risk}
        </span>
      </div>

      <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--text)', margin: '12px 0 0' }}>
        {outlook.plain_summary}
      </p>

      {outlook.key_drivers?.length ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginTop: 14 }}>
          {outlook.key_drivers.map((d) => {
            const Icon = d.direction === 'up' ? ArrowUpRight : d.direction === 'down' ? ArrowDownRight : Minus
            const col = d.direction === 'up' ? 'var(--pos)' : d.direction === 'down' ? 'var(--neg)' : 'var(--text-faint)'
            return (
              <div key={d.name} className="card" style={{ padding: '10px 13px', background: 'var(--bg-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Icon size={14} style={{ color: col }} />
                  <b style={{ fontSize: 13 }}>{d.name}</b>
                </div>
                <div className="num" style={{ fontSize: 16, fontWeight: 700, margin: '3px 0' }}>{d.value}</div>
                <div className="faint" style={{ fontSize: 12 }}>{d.meaning}</div>
              </div>
            )
          })}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 14, fontSize: 12.5, color: 'var(--text-dim)' }}>
        {outlook.realized_vol != null ? (
          <span><b>Realized volatility:</b> {outlook.realized_vol.toFixed(1)}% annualized</span>
        ) : null}
        {outlook.news_influence ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <Newspaper size={13} />
            <b>News tone:</b> {outlook.news_influence.tone} ({outlook.news_influence.score >= 0 ? '+' : ''}{outlook.news_influence.score.toFixed(2)}, {outlook.news_influence.method}-tagged)
          </span>
        ) : null}
      </div>

      {outlook.watch_next?.length ? (
        <div style={{ marginTop: 13, padding: '10px 13px', borderRadius: 10, background: 'color-mix(in srgb, var(--neutral) 8%, transparent)', display: 'flex', gap: 8 }}>
          <AlertTriangle size={14} style={{ color: 'var(--neutral)', flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: 12.5, color: 'var(--text-dim)' }}>
            <b style={{ color: 'var(--text)' }}>What would change this read:</b>{' '}
            <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
              {outlook.watch_next.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </div>
        </div>
      ) : null}

      {outlook.logic_note ? (
        <div className="faint" style={{ fontSize: 11.5, marginTop: 12, fontStyle: 'italic' }}>{outlook.logic_note}</div>
      ) : null}
    </div>
  )
}
