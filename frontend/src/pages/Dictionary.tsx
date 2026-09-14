import { useMemo, useState } from 'react'
import { BookMarked, Search } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { CardSkeleton } from '../components/Skeletons'
import type { DictionaryTerm } from '../types'

export function DictionaryPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { data, loading, error } = useApi<{ count: number; terms: DictionaryTerm[] }>('/api/dictionary')
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('')

  const cats = useMemo(() => {
    const s = new Set<string>()
    data?.terms.forEach((t) => s.add(t.category))
    return Array.from(s).sort()
  }, [data])

  const filtered = useMemo(() => {
    let terms = data?.terms ?? []
    if (cat) terms = terms.filter((t) => t.category === cat)
    if (q.trim()) {
      const ql = q.toLowerCase()
      terms = terms.filter((t) => t.term.toLowerCase().includes(ql) || t.definition.toLowerCase().includes(ql))
    }
    return terms
  }, [data, q, cat])

  return (
    <div>
      <h1 className="page-title">Financial Dictionary</h1>
      <p className="page-sub">{data?.count ?? '…'} beginner-friendly terms. No jargon walls — every definition says what it means and why it matters.</p>

      <div style={{ position: 'relative', maxWidth: 560, marginBottom: 12 }}>
        <Search size={16} style={{ position: 'absolute', left: 13, top: 13, color: 'var(--text-faint)' }} />
        <input
          className="search-input"
          style={{ padding: '11px 14px 11px 40px', fontSize: 14 }}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search a term — e.g. RSI, FII, VWAP…"
        />
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
        <button className={`btn ${cat === '' ? 'primary' : 'ghost'}`} style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => setCat('')}>All</button>
        {cats.map((c) => (
          <button key={c} className={`btn ${cat === c ? 'primary' : 'ghost'}`} style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => setCat(c)}>{c}</button>
        ))}
      </div>

      {error ? <div className="err-box">{error}</div> : null}
      {loading && !data ? <CardSkeleton height={300} /> : null}
      <div className="grid cols-2">
        {filtered.map((t) => (
          <div className="card" key={t.term}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookMarked size={14} style={{ color: 'var(--accent-a)', flexShrink: 0 }} />
              <b style={{ fontSize: 14.5 }}>{t.term}</b>
              <span className="chip" style={{ marginLeft: 'auto' }}>{t.category}</span>
            </div>
            <p style={{ fontSize: 13.5, color: 'var(--text-dim)', margin: '9px 0 8px', lineHeight: 1.6 }}>{t.definition}</p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              {t.see_also?.map((s) => (
                <button key={s} className="chip" onClick={() => setQ(s)} style={{ cursor: 'pointer' }}>↳ {s}</button>
              ))}
              <button
                className="btn ghost"
                style={{ fontSize: 11.5, padding: '3px 9px', marginLeft: 'auto' }}
                onClick={() => onExplain(`The term "${t.term}": ${t.definition}`)}
              >
                ✨ Explain simpler (PA)
              </button>
            </div>
          </div>
        ))}
      </div>
      {!loading && !filtered.length ? <p className="muted" style={{ textAlign: 'center' }}>No terms match “{q}”. Try a shorter query or ask the Pulse Assistant.</p> : null}
    </div>
  )
}
