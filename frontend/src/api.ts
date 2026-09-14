/** Typed API client. Dev: same-origin via Vite proxy. Prod: VITE_API_BASE_URL. */

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<{ status: string; ai_available: boolean; data_mode: string }>('/api/health'),
  overview: () => get<import('./types').Overview>('/api/overview'),
  search: (q: string) =>
    get<{ query: string; results: import('./types').Instrument[] }>(`/api/search?q=${encodeURIComponent(q)}`),
  asset: (id: string) => get<import('./types').AssetDetail>(`/api/asset/${id}`),
  analysis: (id: string) => get<import('./types').Analysis>(`/api/analysis/${id}`),
  news: (topic = 'global') => get<{ topic: string; aggregate_score: number; method: string; articles: import('./types').NewsArticle[] }>(`/api/news?topic=${topic}`),
  chat: (question: string, instrument_id?: string) =>
    post<{ answer: string; generated_by: string }>('/api/chat', { question, instrument_id }),
  assistant: (mode: 'qa' | 'explain', text: string, context?: Record<string, unknown>) =>
    post<{ answer: string; generated_by: string }>('/api/assistant', { mode, text, context }),
  analyzeImage: (image_b64: string, mime: string) =>
    post<{ text: string; generated_by: string }>('/api/analyze-image', { image_b64, mime }),
  fx: (base = 'USD') => get<import('./types').FXData>(`/api/fx?base=${base}`),
  fxConvert: (amount: number, from_currency: string, to_currency: string) =>
    post<{ amount: number; from: string; to: string; result: number | null }>('/api/fx/convert', { amount, from_currency, to_currency }),
  recap: () => get<{ text: string; generated_by: string; data_mode: string }>('/api/recap'),
  dictionary: (q = '', category = '') =>
    get<{ count: number; terms: import('./types').DictionaryTerm[] }>(`/api/dictionary?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}`),
  methodology: () => get<import('./types').Methodology>('/api/methodology'),
  demoToggle: (enabled: boolean) => post<{ demo_mode: boolean }>('/api/demo/toggle', { enabled }),
}

export const DISCLAIMER = 'Educational information — not investment advice.'
