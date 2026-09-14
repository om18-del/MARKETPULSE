import { Activity, Waves, Wind, GitBranch } from 'lucide-react'
import type { Analysis } from '../types'

export function FilterReadout({ filters, cross }: { filters: Analysis['filters']; cross: Analysis['cross_asset'] }) {
  const v = filters.vwap
  const vp = filters.volume_pressure
  const vv = filters.vix_velocity
  const zTone = v ? (v.band === 'extended' ? 'warn' : 'pos') : undefined
  return (
    <div>
      <div className="grid cols-3">
        <div className="card" style={{ padding: 0 }}>
          <div className="card-title" style={{ padding: '12px 13px 0', margin: 0 }}><Waves size={14} /> VWAP Z-Score</div>
          {v ? (
            <div style={{ padding: '0 13px 13px' }}>
              <div className="num" style={{ fontSize: 21, fontWeight: 700, color: zTone === 'warn' ? 'var(--neutral)' : 'var(--text)' }}>
                {v.zscore >= 0 ? '+' : ''}{v.zscore.toFixed(2)}σ
              </div>
              <span className={`chip ${v.band === 'extended' ? 'neutral' : v.band === 'stretched' ? 'uncertain' : 'pos'}`}>{v.band}</span>
              <div className="faint" style={{ marginTop: 6 }}>{v.rule}</div>
            </div>
          ) : (
            <div className="muted" style={{ padding: 13 }}>insufficient data</div>
          )}
        </div>

        <div className="card" style={{ padding: 0 }}>
          <div className="card-title" style={{ padding: '12px 13px 0', margin: 0 }}><Wind size={14} /> VIX Velocity</div>
          {vv ? (
            <div style={{ padding: '0 13px 13px' }}>
              <div className="num" style={{ fontSize: 21, fontWeight: 700 }}>
                {vv.change_pct_5d >= 0 ? '+' : ''}{vv.change_pct_5d.toFixed(1)}%
              </div>
              <span className={`chip ${vv.regime === 'spiking' ? 'neg' : vv.regime === 'collapsing' ? 'pos' : 'neutral'}`}>{vv.regime}</span>
              <div className="faint" style={{ marginTop: 6 }}>z {vv.zscore >= 0 ? '+' : ''}{vv.zscore.toFixed(2)} · {vv.rule}</div>
            </div>
          ) : (
            <div className="muted" style={{ padding: 13 }}>VIX data unavailable</div>
          )}
        </div>

        <div className="card" style={{ padding: 0 }}>
          <div className="card-title" style={{ padding: '12px 13px 0', margin: 0 }}><Activity size={14} /> Volume Pressure <span className="chip" style={{ fontSize: 9 }}>proxy</span></div>
          {vp ? (
            <div style={{ padding: '0 13px 13px' }}>
              <div style={{ fontSize: 16, fontWeight: 700, textTransform: 'capitalize', color: vp.proxy_label === 'accumulation' ? 'var(--pos)' : vp.proxy_label === 'distribution' ? 'var(--neg)' : 'var(--text)' }}>
                {vp.proxy_label}
              </div>
              <div className="faint num" style={{ marginTop: 4 }}>
                up/down {vp.updown_ratio?.toFixed(2) ?? '—'} · OBV slope {vp.obv_slope?.toFixed(2) ?? '—'} · vol z {vp.volume_zscore?.toFixed(1) ?? '—'}
              </div>
              <div className="faint" style={{ marginTop: 4 }}>{vp.rule}</div>
            </div>
          ) : (
            <div className="muted" style={{ padding: 13 }}>insufficient data</div>
          )}
        </div>
      </div>

      {cross?.drivers && Object.keys(cross.drivers).length ? (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-title"><GitBranch size={15} /> Cross-Asset Pressure Matrix <span className="faint" style={{ textTransform: 'none', letterSpacing: 0 }}>{cross.summary}</span></div>
          <table className="tbl">
            <thead>
              <tr><th>Driver</th><th>Correlation (60d)</th><th>5d lead agreement</th><th>Driver 5d move</th></tr>
            </thead>
            <tbody>
              {Object.entries(cross.drivers).map(([k, d]) => (
                <tr key={k}>
                  <td style={{ textTransform: 'uppercase', fontWeight: 700 }}>{k}</td>
                  <td className="num">{d.correlation >= 0 ? '+' : ''}{d.correlation.toFixed(2)}</td>
                  <td className="num">{d.lead5d_agreement != null ? `${(d.lead5d_agreement * 100).toFixed(0)}%` : '—'}</td>
                  <td className="num" style={{ color: d.d5_change_pct >= 0 ? 'var(--pos)' : 'var(--neg)' }}>
                    {d.d5_change_pct >= 0 ? '+' : ''}{d.d5_change_pct.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="faint" style={{ marginTop: 10 }}>
            Correlation ≠ causation. This shows how the asset has recently co-moved with macro drivers — context, not prophecy.
          </p>
        </div>
      ) : null}
    </div>
  )
}
