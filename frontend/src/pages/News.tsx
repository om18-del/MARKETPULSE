import { useState } from 'react'
import { Newspaper } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { NewsList } from '../components/NewsList'
import { CardSkeleton } from '../components/Skeletons'

const TOPICS = [
  { id: 'global', label: '🌍 Global' },
  { id: 'us', label: '🇺🇸 US' },
  { id: 'india', label: '🇮🇳 India' },
  { id: 'macro', label: '🏦 Macro & Rates' },
  { id: 'commodities', label: '🛢 Commodities' },
  { id: 'fx', label: '💱 Currencies' },
]

interface NewsPayload {
  topic: string
  aggregate_score: number
  method: string
  articles: import('../types').NewsArticle[]
  summary?: string
  fetched_at?: string
  disclaimer: string
}

export function NewsPage() {
  const [topic, setTopic] = useState('global')
  const { data, loading, error } = useApi<NewsPayload>(`/api/news?topic=${topic}`)

  return (
    <div>
      <h1 className="page-title">Market news, tagged honestly</h1>
      <p className="page-sub">
        Headlines with an AI sentiment tag — and the exact phrase that drove each tag, so you can judge for yourself.
        Every item links to the original publisher.
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
        {TOPICS.map((t) => (
          <button key={t.id} className={`btn ${topic === t.id ? 'primary' : 'ghost'}`} style={{ padding: '7px 14px', fontSize: 13 }} onClick={() => setTopic(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {error ? <div className="err-box">{error} <button className="btn" onClick={() => location.reload()}>Retry</button></div> : null}
      {loading && !data ? <CardSkeleton height={280} /> : null}
      {data ? (
        <div className="card">
          <div className="card-title">
            <Newspaper size={15} /> {TOPICS.find((t) => t.id === topic)?.label} headlines
            <span className={`chip ${data.aggregate_score > 0.1 ? 'pos' : data.aggregate_score < -0.1 ? 'neg' : 'neutral'}`} style={{ marginLeft: 'auto' }}>
              overall tone {data.aggregate_score >= 0 ? '+' : ''}{data.aggregate_score.toFixed(2)} · {data.method === 'gemini' ? 'AI-tagged' : data.method}
            </span>
          </div>
          {data.summary ? <p className="muted" style={{ fontSize: 13.5, marginTop: -4 }}>{data.summary}</p> : null}
          <NewsList articles={data.articles} />
          <p className="faint" style={{ marginTop: 12 }}>
            Sentiment tags describe the likely market impact of each headline's wording — they are context, not advice.
          </p>
        </div>
      ) : null}
    </div>
  )
}
