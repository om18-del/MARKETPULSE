import { useState } from 'react'
import { Clock, Volume2 } from 'lucide-react'
import { api } from '../api'
import { useSpeech } from '../hooks/useSpeech'

export function RecapCard() {
  const [text, setText] = useState<string | null>(null)
  const [by, setBy] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const speech = useSpeech()

  const gen = async () => {
    setBusy(true)
    setErr(null)
    try {
      const r = await api.recap()
      setText(r.text)
      setBy(r.generated_by)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        <Clock size={15} /> Daily 60-second recap
        <button className="btn primary" style={{ marginLeft: 'auto', padding: '6px 13px', fontSize: 12.5 }} onClick={gen} disabled={busy}>
          {busy ? 'generating…' : text ? 'Regenerate' : 'Generate'}
        </button>
      </div>
      {err ? <div className="err-box">{err}</div> : null}
      {text ? (
        <>
          <div style={{ fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{text}</div>
          <div style={{ display: 'flex', gap: 10, marginTop: 10, alignItems: 'center' }}>
            <span className="chip">{by === 'gemini-analysis' ? 'AI-generated' : 'deterministic'}</span>
            {speech.ttsSupported ? (
              <button className="btn ghost" style={{ fontSize: 12.5 }} onClick={() => (speech.speaking ? speech.stopSpeaking() : speech.speak(text))}>
                <Volume2 size={13} /> {speech.speaking ? 'Stop' : 'Read aloud'}
              </button>
            ) : null}
          </div>
        </>
      ) : (
        !err && <p className="muted" style={{ fontSize: 13.5 }}>One tap gives you today's market story: global read, biggest mover, volatility, and what to watch — in plain words.</p>
      )}
    </div>
  )
}
