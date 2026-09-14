import { useEffect, useRef, useState } from 'react'
import { Mic, MessagesSquare, Send, Volume2, VolumeX } from 'lucide-react'
import { api } from '../api'
import { useSpeech } from '../hooks/useSpeech'
import { SearchBar } from '../components/SearchBar'

interface Msg {
  role: 'user' | 'bot'
  text: string
  by?: string
}

const SUGGESTIONS = [
  'Why is the global verdict what it is today?',
  'What does the VIX tell us right now?',
  'Which asset had the strongest trend and why?',
  'Explain the biggest mover in simple words.',
]

export function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: 'bot',
      text:
        'This is the Analysis chat — grounded in today\'s live data, regime scores and news.\n\nAsk about the current market state (never for advice). For simple word-explanations, use the Pulse Assistant bubble instead.\n\nEducational information — not investment advice.',
    },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [focusId, setFocusId] = useState<string | undefined>(undefined)
  const bodyRef = useRef<HTMLDivElement>(null)
  const speech = useSpeech()

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [msgs])

  useEffect(() => {
    if (speech.transcript) setInput(speech.transcript)
  }, [speech.transcript])

  const send = async (text: string) => {
    const t = text.trim()
    if (!t || busy) return
    setMsgs((m) => [...m, { role: 'user', text: t }])
    setInput('')
    setBusy(true)
    try {
      const res = await api.chat(t, focusId)
      setMsgs((m) => [...m, { role: 'bot', text: res.answer, by: res.generated_by }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'bot', text: `Sorry — ${e instanceof Error ? e.message : 'request failed'}.` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Analysis chat</h1>
      <p className="page-sub">
        Answers are generated from <b>today's actual numbers</b> — regime equations, filters and headlines — never
        invented. Optionally focus it on one asset: search below, then ask.
      </p>

      <div style={{ maxWidth: 620, marginBottom: 8 }}>
        <SearchBar />
        <div className="faint" style={{ marginTop: 6, textAlign: 'center' }}>
          optional: the asset you open from search becomes the chat's focus — <button className="btn ghost" style={{ fontSize: 11, padding: '2px 8px' }} onClick={() => setFocusId(undefined)}>use whole market</button>
        </div>
      </div>

      <div className="card" style={{ height: '54vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
        <div className="pa-body" ref={bodyRef} style={{ flex: 1 }}>
          {msgs.map((m, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%' }}>
              <div className={`pa-msg ${m.role}`} style={{ maxWidth: '86%' }}>{m.text}</div>
              {m.role === 'bot' && i > 0 ? (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="pa-tag">{m.by}</span>
                  {speech.ttsSupported ? (
                    <button
                      aria-label="Read aloud"
                      onClick={() => (speech.speaking ? speech.stopSpeaking() : speech.speak(m.text))}
                      style={{ background: 'none', border: 'none', color: 'var(--text-faint)', padding: 2 }}
                    >
                      {speech.speaking ? <VolumeX size={13} /> : <Volume2 size={13} />}
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
          {busy ? <div className="pa-msg bot">crunching the numbers…</div> : null}
        </div>
        <div className="pa-input">
          {speech.srSupported ? (
            <button className="btn ghost" style={{ padding: 8 }} onClick={() => (speech.listening ? speech.stopListening() : speech.startListening())} aria-label="Voice input">
              <Mic size={15} color={speech.listening ? 'var(--neg)' : 'var(--text-dim)'} />
            </button>
          ) : null}
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send(input)}
            placeholder="Ask about today's market state…"
          />
          <button className="btn primary" style={{ padding: '8px 12px' }} onClick={() => send(input)} disabled={busy} aria-label="Send">
            <Send size={15} />
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        <MessagesSquare size={15} style={{ color: 'var(--text-faint)', marginTop: 6 }} />
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" style={{ cursor: 'pointer' }} onClick={() => send(s)}>
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
