import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'

export function AboutPage() {
  return (
    <div>
      <h1 className="page-title">About MarketPulse</h1>
      <p className="page-sub">An AI market-literacy platform for the Indian market (NSE): every NSE-listed company, keyless data straight from nseindia.com, INR by default — and every verdict backed by visible evidence.</p>

      <div className="grid cols-2">
        <div className="card">
          <div className="card-title">What MarketPulse IS</div>
          <ul style={{ fontSize: 13.5, color: 'var(--text-dim)', paddingLeft: 18, lineHeight: 1.9 }}>
            <li>A decision-<b>support</b> and learning tool for Indian retail investors</li>
            <li>India-first: NIFTY family, NSE equities and USD/INR lead every read — with global context alongside</li>
            <li>Data <b>directly from nseindia.com</b> (keyless) with a global provider fallback chain</li>
            <li>Deterministic math first — the AI only translates it</li>
            <li>Fully explainable: every verdict shows its evidence and its equation</li>
            <li>Self-auditing: the Methodology page documents every rule</li>
          </ul>
        </div>
        <div className="card" style={{ borderColor: 'color-mix(in srgb, var(--neutral) 35%, transparent)' }}>
          <div className="card-title"><ShieldCheck size={15} /> What MarketPulse is NOT</div>
          <ul style={{ fontSize: 13.5, color: 'var(--text-dim)', paddingLeft: 18, lineHeight: 1.9 }}>
            <li>Not investment advice — ever, anywhere in the app</li>
            <li>Not a trading bot; no buy/sell signals, no automation</li>
            <li>Not a prediction engine — verdicts describe the present only</li>
            <li>Not a broker; no orders, no portfolios, no payments</li>
            <li>Not guaranteed-accurate: providers and models can err — evidence is shown so you can verify</li>
          </ul>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">How it works — the short version</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {[
            ['1 · Ingest', 'NSE India first: equities, indices, NIFTY-50 breadth and the full listed-company universe straight from nseindia.com (keyless). Fallbacks: Stooq → ECB Frankfurter → Twelve Data → Finnhub → Alpha Vantage — all validated, cached and circuit-broken.'],
            ['2 · Compute', 'A deterministic math layer computes SMAs, RSI, MACD, ATR, realized vol, VWAP z-scores, VIX velocity, OBV/volume pressure and cross-asset correlations.'],
            ['3 · Score', 'The regime engine blends Trend 35% + Momentum 25% + Volatility 25% + Volume 15% + news ±10% into a 0-100 score → Bullish / Bearish / Neutral / Uncertain.'],
            ['4 · Explain', 'Gemini translates the numeric payload into structured theses; the Pulse Assistant explains any selected text in simpler words. Every number traces back to the evidence panel.'],
          ].map(([t, d]) => (
            <div key={t} className="card" style={{ background: 'var(--bg-soft)' }}>
              <b style={{ color: 'var(--accent-a)', fontSize: 13.5 }}>{t}</b>
              <p style={{ fontSize: 12.5, color: 'var(--text-dim)', margin: '6px 0 0' }}>{d}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">Data & AI provenance</div>
        <p style={{ fontSize: 13.5, color: 'var(--text-dim)' }}>
          Market data: <b>nseindia.com directly (keyless, India-first)</b>, then Stooq (keyless), Frankfurter/ECB (keyless FX),
          optional Twelve Data / Finnhub / Alpha Vantage.
          News: Google News RSS with publisher attribution. AI: Google Gemini (flash model) via server-side key —
          prompts are constrained against advice and predictions, and a deterministic fallback keeps the app useful
          when AI is unavailable. When live data is unreachable, the app switches to clearly-labeled Demo Mode.
        </p>
        <p style={{ fontSize: 13.5, color: 'var(--text-dim)' }}>
          Explore the full details on the <Link to="/methodology" style={{ color: 'var(--accent-a)' }}>Methodology page</Link>.
        </p>
      </div>

      <p className="faint" style={{ textAlign: 'center', marginTop: 26 }}>
        Built for educational purposes. Markets involve risk; past behavior never guarantees future outcomes.
      </p>
    </div>
  )
}
