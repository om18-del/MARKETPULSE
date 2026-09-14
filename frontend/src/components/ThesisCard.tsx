import { useState } from 'react'
import { Sparkles, Volume2 } from 'lucide-react'
import { useSpeech } from '../hooks/useSpeech'

export function ThesisCard({ thesis, onExplain }: { thesis: { text: string; generated_by: string }; onExplain: (t: string) => void }) {
  const speech = useSpeech()
  const [selected, setSelected] = useState('')

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
