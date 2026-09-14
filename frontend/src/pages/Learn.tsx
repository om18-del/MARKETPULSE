import { useState } from 'react'
import { BookOpen, CheckCircle2, GraduationCap, XCircle } from 'lucide-react'

const LESSONS = [
  {
    title: '1 · How to read this dashboard',
    minutes: 3,
    points: [
      'The big gauge is the global regime: where the whole market leans today — Bullish, Bearish, Neutral or Uncertain.',
      'It is a weighted blend: Trend 35%, Momentum 25%, Volatility 25%, Volume 15%, news up to ±10%.',
      'Every number has an Evidence panel: click any asset to see each factor, its rule, and its contribution.',
      'High volatility pushes reads toward "Uncertain" — that is honesty, not weakness.',
    ],
  },
  {
    title: '2 · What is volatility, really?',
    minutes: 4,
    points: [
      'Volatility = how much prices swing. Realized volatility measures actual recent swings; VIX measures expected swings.',
      'High volatility means bigger moves both ways — outcomes get harder to anticipate.',
      'VIX Velocity asks: is fear rising FAST? Fast changes in fear often matter more than fear levels.',
      'A volatile market is not a "bad" market — it is an uncertain one. MarketPulse labels it that way.',
    ],
  },
  {
    title: '3 · Why does USD strength matter?',
    minutes: 4,
    points: [
      'The Dollar Index (DXY) measures the USD against major currencies.',
      'When the dollar strengthens, global money often flows toward US assets — pressuring emerging markets like India.',
      'For India specifically: USD/INR up → imports (oil!) cost more in rupees; exports get more competitive.',
      'That is why the cross-asset pressure matrix correlates DXY, crude, gold and 10Y against each index.',
    ],
  },
  {
    title: '4 · Reading volume like an analyst',
    minutes: 3,
    points: [
      'Price tells you WHAT happened; volume hints at WHO was behind it.',
      'Up/down volume ratio compares how much volume traded on up days vs down days.',
      'OBV slope: is cumulative volume flowing with the trend or against it?',
      'Honesty note: this is a proxy. Real institutional order-flow is private — MarketPulse never overclaims.',
    ],
  },
]

const QUIZ: { q: string; options: string[]; answer: number; why: string }[] = [
  { q: 'What does a "bullish" environment mean?', options: ['Prices are expected to be guaranteed to rise', 'The current environment leans toward rising prices', 'Everyone must buy immediately', 'Volatility is high'], answer: 1, why: 'Bullish describes the current lean of the market — never a guarantee or an instruction.' },
  { q: 'RSI at 74 means…', options: ['Buy signal', 'Sell signal', 'The recent run-up is statistically extended (overbought territory)', 'Nothing'], answer: 2, why: 'RSI ≥ 70 flags a stretched move. It is context about extension, not a trading signal.' },
  { q: 'Why does high volatility push a read toward "Uncertain"?', options: ['Because falls always follow', 'Because big swings make outcomes harder to anticipate', 'Because volume disappears', 'It does not'], answer: 1, why: 'Uncertainty is about predictability, not direction. Wild swings reduce reliability of any directional read.' },
  { q: 'What is MarketPulse\'s volume-pressure measure?', options: ['A record of real institutional orders', 'A proxy estimated from public volume data', 'The number of traders online', 'A guaranteed signal'], answer: 1, why: 'Order-flow is private; we estimate pressure from up/down volume and OBV — and label it a proxy.' },
  { q: 'USD/INR rising from 86 to 87 means…', options: ['The rupee strengthened', 'The dollar buys more rupees (rupee weakened)', 'India\'s market crashed', 'Nothing changes'], answer: 1, why: 'USD/INR quotes rupees per dollar. Rising = each dollar costs more rupees = rupee weaker.' },
  { q: 'The news modifier in the regime score is capped at…', options: ['±50%', '±25%', '±10%', 'Unlimited'], answer: 2, why: 'Headlines can influence but never dominate the math — capped at ±10%.' },
  { q: 'Which weight does Trend carry in the regime score?', options: ['35%', '15%', '50%', '25%'], answer: 0, why: 'Trend 35% — position vs moving averages is the most stable beginner-readable signal.' },
  { q: 'A VWAP z-score of +2.4σ suggests…', options: ['Price is statistically extended above its volume-weighted average', 'Time to buy', 'A guaranteed fall', 'Volume is zero'], answer: 0, why: '|z| > 2 = extended move vs recent norms — context, not a signal.' },
  { q: 'MarketPulse can tell you to buy a stock.', options: ['True', 'False — it never advises, only explains with evidence', 'True after market hours', 'Only for indices'], answer: 1, why: 'Strictly educational. It shows evidence; decisions are always yours.' },
  { q: '"What would change this read" lists…', options: ['Future predictions', 'The specific conditions that would flip the verdict', 'Broker recommendations', 'Random tips'], answer: 1, why: 'It makes the analysis falsifiable — you know exactly what evidence would change the conclusion.' },
]

export function LearnPage() {
  const [quizOpen, setQuizOpen] = useState(false)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [submitted, setSubmitted] = useState(false)

  const score = QUIZ.reduce((acc, item, i) => acc + (answers[i] === item.answer ? 1 : 0), 0)

  return (
    <div>
      <h1 className="page-title">Learn</h1>
      <p className="page-sub">Short lessons that teach you to read this dashboard like an analyst — then test yourself.</p>

      <div className="grid cols-2">
        {LESSONS.map((l) => (
          <div className="card" key={l.title}>
            <div className="card-title"><BookOpen size={15} /> {l.title} <span className="faint" style={{ marginLeft: 'auto' }}>{l.minutes} min</span></div>
            {l.points.map((p, i) => (
              <p key={i} style={{ fontSize: 13.5, margin: '8px 0', color: 'var(--text-dim)' }}>• {p}</p>
            ))}
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-title"><GraduationCap size={15} /> Test yourself — 10 questions</div>
        {!quizOpen ? (
          <button className="btn primary" onClick={() => { setQuizOpen(true); setSubmitted(false); setAnswers({}) }}>Start quiz</button>
        ) : (
          <div>
            {QUIZ.map((item, i) => (
              <div key={i} style={{ padding: '14px 0', borderBottom: '1px solid var(--card-border)' }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>{i + 1}. {item.q}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {item.options.map((opt, oi) => {
                    const picked = answers[i] === oi
                    const correct = submitted && oi === item.answer
                    const wrong = submitted && picked && oi !== item.answer
                    return (
                      <button
                        key={oi}
                        onClick={() => !submitted && setAnswers((a) => ({ ...a, [i]: oi }))}
                        className="btn ghost"
                        style={{
                          justifyContent: 'flex-start', fontSize: 13, padding: '8px 12px',
                          borderColor: correct ? 'var(--pos)' : wrong ? 'var(--neg)' : picked ? 'var(--accent-a)' : 'var(--card-border)',
                          color: correct ? 'var(--pos)' : wrong ? 'var(--neg)' : 'var(--text)',
                          opacity: submitted && !picked && !correct ? 0.6 : 1,
                        }}
                      >
                        {correct ? <CheckCircle2 size={14} /> : wrong ? <XCircle size={14} /> : null} {opt}
                      </button>
                    )
                  })}
                </div>
                {submitted ? <div className="faint" style={{ marginTop: 6 }}>Why: {item.why}</div> : null}
              </div>
            ))}
            {!submitted ? (
              <button className="btn primary" style={{ marginTop: 14 }} onClick={() => setSubmitted(true)} disabled={Object.keys(answers).length < QUIZ.length}>
                Submit ({Object.keys(answers).length}/{QUIZ.length} answered)
              </button>
            ) : (
              <div style={{ marginTop: 14, display: 'flex', gap: 12, alignItems: 'center' }}>
                <span className="num" style={{ fontSize: 20, fontWeight: 800 }}>Score: {score}/10</span>
                <span className={`chip ${score >= 8 ? 'pos' : score >= 5 ? 'neutral' : 'neg'}`}>
                  {score >= 8 ? 'Excellent — analyst level!' : score >= 5 ? 'Solid foundation' : 'Revisit the lessons above'}
                </span>
                <button className="btn ghost" onClick={() => { setAnswers({}); setSubmitted(false) }}>Retake</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
