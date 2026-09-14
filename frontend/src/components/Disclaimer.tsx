import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, ShieldAlert } from 'lucide-react'

export const DISCLAIMER_TEXT = 'Educational information — not investment advice.'

export function DisclaimerBar() {
  return (
    <div className="disclaimer-bar">
      <ShieldAlert size={11} style={{ verticalAlign: '-2px' }} /> {DISCLAIMER_TEXT} · MarketPulse shows evidence for
      every number — always read it before trusting any label.
    </div>
  )
}

export function DisclaimerModal() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('marketpulse.disclaimerAck')) {
      setOpen(true)
    }
  }, [])

  const ack = () => {
    localStorage.setItem('marketpulse.disclaimerAck', '1')
    setOpen(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{
            position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(4,8,16,0.72)',
            display: 'grid', placeItems: 'center', padding: 20, backdropFilter: 'blur(4px)',
          }}
          onClick={ack}
        >
          <motion.div
            className="card"
            initial={{ scale: 0.94, y: 12 }}
            animate={{ scale: 1, y: 0 }}
            style={{ maxWidth: 470, padding: 26, background: 'var(--bg-soft)', cursor: 'default' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <AlertTriangle style={{ color: 'var(--neutral)', flexShrink: 0, marginTop: 3 }} />
              <div>
                <h2 style={{ margin: '0 0 8px', fontSize: 19 }}>Before you explore MarketPulse</h2>
                <p style={{ fontSize: 13.5, color: 'var(--text-dim)', margin: '0 0 6px' }}>
                  MarketPulse is an <b>educational market-literacy tool</b>. It does not give investment
                  advice, recommendations, or price predictions — and it will never tell you to buy or
                  sell anything.
                </p>
                <p style={{ fontSize: 13.5, color: 'var(--text-dim)', margin: '0 0 14px' }}>
                  Every verdict you'll see is a <b>snapshot of the current environment</b> computed from
                  public data, shown together with its full evidence. Decisions and risks are always yours.
                </p>
                <button className="btn primary" onClick={ack} style={{ width: '100%', justifyContent: 'center' }}>
                  I understand — continue
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
