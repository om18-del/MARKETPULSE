import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageCircle, Mic, Send, Sparkles, Volume2, VolumeX, X } from 'lucide-react'
import { api } from '../api'
import { useSpeech } from '../hooks/useSpeech'

interface Msg {
  role: 'user' | 'bot'
  text: string
  by?: string
}

/** Selection chip: when the user selects text, show "Explain with PA". */
export function SelectToExplain({ onExplain }: { onExplain: (text: string) => void }) {
  const [chip, setChip] = useState<{ x: number; y: number; text: string } | null>(null)

  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection()
      const text = sel?.toString().trim() ?? ''
      if (text.length > 8 && text.length < 1500) {
        const rect = sel!.getRangeAt(0).getBoundingClientRect()
        setChip({ x: Math.min(window.innerWidth - 160, rect.left + rect.width / 2 - 70), y: rect.top - 42, text })
      } else {
        setChip(null)
      }
    }
    document.addEventListener('selectionchange', handler)
    return () => document.removeEventListener('selectionchange', handler)
  }, [])

  if (!chip) return null
  return (
    <motion.button
      initial={{ opacity: 0, y: 6, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0 }}
      className="sel-chip"
      style={{ left: chip.x, top: chip.y, position: 'fixed' }}
      onClick={() => {
        onExplain(chip.text)
        setChip(null)
      }}
    >
      ✨ Explain with PA
    </motion.button>
  )
}

export function PulseAssistant() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: 'bot',
      text:
        "Hi! I'm the Pulse Assistant 📊\n\nI explain market words and ideas in simple terms — or explain any text you select on a page.\n\nI don't give advice or predictions. Educational information — not investment advice.",
    },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const speech = useSpeech()

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [msgs])

  useEffect(() => {
    if (speech.transcript) setInput(speech.transcript)
  }, [speech.transcript])

  // Global "explain this text" channel: pages dispatch mp:explain, PA opens + explains.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail
      if (!detail) return
      setOpen(true)
      void send(detail, 'explain')
    }
    window.addEventListener('mp:explain', handler)
    return () => window.removeEventListener('mp:explain', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = async (text: string, mode: 'qa' | 'explain' = 'qa') => {
    const t = text.trim()
    if (!t || busy) return
    setMsgs((m) => [...m, { role: 'user', text: t }])
    setInput('')
    setBusy(true)
    try {
      const res = await api.assistant(mode, t, { page: location.pathname })
      setMsgs((m) => [...m, { role: 'bot', text: res.answer, by: res.generated_by }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'bot', text: `Sorry — ${e instanceof Error ? e.message : 'request failed'}.` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <SelectToExplain onExplain={(text) => {
        setOpen(true)
        void send(text, 'explain')
      }} />

      <AnimatePresence>
        {open && (
          <motion.div
            className="pa-drawer"
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
          >
            <div className="pa-head">
              <div className="brand-pulse"><Sparkles size={16} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>Pulse Assistant</div>
                <div className="faint">explains · never advises</div>
              </div>
              <button className="btn ghost" style={{ padding: 6 }} onClick={() => setOpen(false)} aria-label="Close assistant">
                <X size={16} />
              </button>
            </div>
            <div className="pa-body" ref={bodyRef}>
              {msgs.map((m, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <div className={`pa-msg ${m.role}`}>{m.text}</div>
                  {m.role === 'bot' && i > 0 ? (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span className="pa-tag">{m.by === 'faq-knowledge-base' ? 'offline knowledge base' : m.by}</span>
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
              {busy ? <div className="pa-msg bot">thinking…</div> : null}
            </div>
            <div className="pa-input">
              {speech.srSupported ? (
                <button
                  className="btn ghost"
                  style={{ padding: 8 }}
                  onClick={() => (speech.listening ? speech.stopListening() : speech.startListening())}
                  aria-label="Voice input"
                >
                  <Mic size={15} color={speech.listening ? 'var(--neg)' : 'var(--text-dim)'} />
                </button>
              ) : null}
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && send(input)}
                placeholder="Ask anything about markets…"
              />
              <button className="btn primary" style={{ padding: '8px 12px' }} onClick={() => send(input)} disabled={busy} aria-label="Send">
                <Send size={15} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        className="pa-fab"
        onClick={() => setOpen((o) => !o)}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Open Pulse Assistant"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </motion.button>
    </>
  )
}
