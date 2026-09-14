import { useState } from 'react'
import { ChevronDown, ListChecks, Sparkles, Volume2 } from 'lucide-react'
import { useSpeech } from '../hooks/useSpeech'

export function ThesisCard({ thesis, onExplain, equation }: { thesis: { text: string; generated_by: string }; onExplain: (t: string) => void; equation?: string }) {
  const speech = useSpeech()
  const [selected, setSelected] = useState('')
  const [showAlgo, setShowAlgo] = useState(false)

  const sections = thesis.text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)

  return (
    <div className="card">
      <div className="card-title">
        <Sparkles size={15} /> Analyst thesis
        <span className="chip" style={{ marginLeft: 'auto' }}>
          {thesis.generated_by === 'gemini-analysis' ? 'AI-generated from the math' : 'deterministic template'}
        </span>
      </div>

      {/* How we got this answer — the algorithm, in the open */}
      <button
        onClick={() => setShowAlgo(!showAlgo)}
        className="btn ghost"
        style={{ fontSize: 12, padding: '5px 11px', marginBottom: 12 }}
      >
        <ListChecks size={13} /> How we got this answer
        <ChevronDown size={12} style={{ transform: showAlgo ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
      </button>
      {showAlgo ? (
        <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '12px 14px', marginBottom: 14, fontSize: 12.5 }}>
          <div style={{ display: 'grid', gap: 6 }}>
            <div>1️⃣ <b>Data:</b> daily OHLCV history pulled from the provider chain (label shown above — live or demo), sanitized and staleness-checked.</div>
            <div>2️⃣ <b>Deterministic math:</b> SMA/RSI/MACD/ATR/realized-vol, VWAP z-score, VIX velocity, volume-pressure proxy and the cross-asset pressure matrix — all computed in code, never by the AI.</div>
            <div>3️⃣ <b>Score:</b> the regime engine blends Trend 35% + Momentum 25% + Volatility 25% + Volume 15% + news ±10% → the verdict and confidence above.</div>
            <div>4️⃣ <b>AI translation:</b> Gemini receives these computed numbers as JSON and writes the words below — it is forbidden from inventing numbers, advising, or predicting.</div>
            {equation ? <div className="equation" style={{ marginTop: 6 }}>{equation}</div> : null}
          </div>
        </div>
      ) : null}
      <div
        style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14, lineHeight: 1.65 }}
        onMouseUp={() => {
          const t = window.getSelection()?.toString().trim() ?? ''
          if (t.length > 8) setSelected(t)
        }}
      >
        {sections.map((line, i) => {
          const [label, ...rest] = line.split(':')
          const isLabeled = rest.length > 0 && label.length < 34
          return isLabeled ? (
            <p key={i} style={{ margin: 0 }}>
              <b style={{ color: 'var(--accent-a)' }}>{label}:</b>
              {rest.join(':')}
            </p>
          ) : (
            <p key={i} style={{ margin: 0 }}>{line}</p>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 14, alignItems: 'center' }}>
        <button className="btn ghost" style={{ fontSize: 12.5 }} onClick={() => selected && onExplain(selected)} disabled={!selected}>
          <Sparkles size={13} /> Explain selection with PA
        </button>
        {speech.ttsSupported ? (
          <button className="btn ghost" style={{ fontSize: 12.5 }} onClick={() => (speech.speaking ? speech.stopSpeaking() : speech.speak(thesis.text))}>
            <Volume2 size={13} /> {speech.speaking ? 'Stop' : 'Read aloud'}
          </button>
        ) : null}
        <span className="faint">Tip: select any line → the chip explains it simply.</span>
      </div>
    </div>
  )
}
