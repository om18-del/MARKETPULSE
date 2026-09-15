import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Globe2, Search, Star, X } from 'lucide-react'

const KEY = 'marketpulse.tourDone'
const STEPS = [
  {
    icon: Globe2,
    title: 'Welcome to MarketPulse',
    body: 'An AI decision-support dashboard for the Indian market (NSE + BSE). It reads 20 indicators, news and market sentiment — and explains the logic behind every answer. Zero black box.',
    pos: 'center' as const,
    cta: 'Show me around · 30s',
  },
  {
    icon: Search,
    title: 'Search any listed company',
    body: 'Type a name (Tata, Reliance…) or a ticker — RELIANCE.NS for NSE, SBIN.BO for BSE. Every result opens a full page: price, chart, and AI analysis with the reasoning shown.',
    pos: 'top' as const,
    cta: 'Next',
  },
  {
    icon: Star,
    title: 'Watch what matters to you',
    body: 'Tap ☆ Watch on any asset and it lands in your Watchlist — live closes, changes, and the same deep analysis one tap away. The Overview board keeps the whole market in view.',
    pos: 'top' as const,
    cta: 'Start exploring',
  },
]

export function OnboardingTour() {
  const [step, setStep] = useState(0)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (localStorage.getItem(KEY)) return
    // Start only after the disclaimer modal is acknowledged — never stack modals.
    const poll = setInterval(() => {
      if (localStorage.getItem('marketpulse.disclaimerAck')) {
        clearInterval(poll)
        setTimeout(() => setOpen(true), 900)
      }
    }, 700)
    const stop = setTimeout(() => clearInterval(poll), 25000)
    return () => {
      clearInterval(poll)
      clearTimeout(stop)
    }
  }, [])

  if (!open) return null
  const s = STEPS[step]
  const Icon = s.icon
  const last = step === STEPS.length - 1

  const finish = () => {
    localStorage.setItem(KEY, '1')
    setOpen(false)
  }

  const cardPos =
    s.pos === 'center'
      ? { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', maxWidth: 420 }
      : { top: 64, left: '50%', transform: 'translateX(-50%)', maxWidth: 400 }

  return (
    <AnimatePresence>
      <motion.div
        key={step}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25 }}
        className="card"
        style={{
          position: 'fixed', zIndex: 190, padding: '18px 20px', ...cardPos,
          borderColor: 'color-mix(in srgb, var(--accent-a) 45%, transparent)',
          boxShadow: '0 18px 50px rgba(0,0,0,0.45)',
        }}
        role="dialog"
        aria-label="Onboarding tour"
      >
        <button
          onClick={finish}
          aria-label="Skip tour"
          style={{ position: 'absolute', top: 10, right: 10, background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer' }}
        >
          <X size={15} />
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <span className="brand-pulse"><Icon size={16} /></span>
          <strong style={{ fontSize: 15 }}>{s.title}</strong>
        </div>
        <p className="muted" style={{ margin: '10px 0 12px', fontSize: 13.5, lineHeight: 1.55 }}>
          {s.body}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: 5 }}>
            {STEPS.map((_, i) => (
              <span
                key={i}
                style={{
                  width: i === step ? 18 : 7,
                  height: 7,
                  borderRadius: 999,
                  background: i === step ? 'var(--accent-a)' : 'var(--card-border)',
                  transition: 'width 0.2s',
                }}
              />
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {step > 0 && (
              <button className="btn ghost" style={{ padding: '6px 12px' }} onClick={() => setStep((v) => v - 1)}>
                Back
              </button>
            )}
            <button className="btn primary" style={{ padding: '6px 14px' }} onClick={() => (last ? finish() : setStep((v) => v + 1))}>
              {s.cta}
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
