import { ExternalLink } from 'lucide-react'
import type { NewsArticle } from '../types'

function sentimentChip(s?: number) {
  if (s === undefined) return <span className="chip">—</span>
  const cls = s > 0.15 ? 'pos' : s < -0.15 ? 'neg' : 'neutral'
  const label = s > 0.15 ? 'positive' : s < -0.15 ? 'negative' : 'neutral'
  return <span className={`chip ${cls}`}>{label} {s >= 0 ? '+' : ''}{s.toFixed(2)}</span>
}

export function NewsList({ articles, showReason = true }: { articles: NewsArticle[]; showReason?: boolean }) {
  if (!articles?.length) return <p className="muted" style={{ fontSize: 14 }}>No headlines available right now.</p>
  return (
    <div>
      {articles.map((a, i) => (
        <div key={i} style={{ padding: '12px 0', borderBottom: '1px solid var(--card-border)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <a href={a.link} target="_blank" rel="noreferrer" style={{ fontWeight: 600, fontSize: 14, display: 'inline-flex', gap: 6, alignItems: 'baseline' }}>
                {a.title} <ExternalLink size={12} style={{ flexShrink: 0 }} />
              </a>
              <div className="faint" style={{ marginTop: 3 }}>
                {a.publisher}{a.published ? ` · ${a.published}` : ''}
                {a.method ? ` · ${a.method === 'gemini' ? 'AI-tagged' : 'keyword-tagged'}` : ''}
              </div>
              {showReason && a.reason ? (
                <div className="faint" style={{ marginTop: 3, color: 'var(--text-dim)' }}>
                  Why: {a.reason}{a.key_phrase ? ` — "${a.key_phrase}"` : ''}
                </div>
              ) : null}
            </div>
            <div style={{ flexShrink: 0 }}>{sentimentChip(a.sentiment)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
