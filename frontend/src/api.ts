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
    get<{ query: string; results: import('./types').Instrument[]; nse_universe?: boolean }>(`/api/search?q=${encodeURIComponent(q)}`),
  asset: (id: string) => get<import('./types').AssetDetail>(`/api/asset/${id}`),
  analysis: (id: string) => get<import('./types').Analysis>(`/api/analysis/${id}`),
  analysisProgress: (id: string) =>
    get<import('./components/LoadingProgress').AnalysisProgress>(`/api/analysis/${encodeURIComponent(id)}/progress`),
  news: (topic = 'india') => get<{ topic: string; aggregate_score: number; method: string; articles: import('./types').NewsArticle[] }>(`/api/news?topic=${topic}`),
  nseMovers: () =>
    get<{ available: boolean; gainers: { symbol: string; name: string; last_price: number; change_pct: number }[]; losers: { symbol: string; name: string; last_price: number; change_pct: number }[]; advances: number | null; declines: number | null; counted: number; reason?: string }>(`/api/nse/movers`),
  scanner: () =>
    get<{ universe: string; scanned: number; aligned: number; conflicts: { symbol: string; intraday: 'BULLISH' | 'BEARISH' | 'NEUTRAL'; daily: 'BULLISH' | 'BEARISH' | 'NEUTRAL'; intraday_ret?: number | null; last_close?: number; conflict: string }[]; note?: string; disclaimer?: string }>(`/api/scanner/intraday-conflicts`),
  integrity: () =>
    get<{ checked: number; problems_found: number; problems: { instrument: string; issue: string; detail: string }[]; newest_data_date?: string; verdict: string; note?: string }>(`/api/integrity`),
  watchlistQuotes: (ids: string[]) =>
    post<{ requested: number; found: number; quotes: { id: string; name: string; currency: string; price: number; change_pct: number; data_date: string; demo: boolean }[]; disclaimer: string }>('/api/watchlist/quotes', { ids }),
  chat: (question: string, instrument_id?: string) =>
    post<{ answer: string; generated_by: string }>('/api/chat', { question, instrument_id }),
  assistant: (mode: 'qa' | 'explain', text: string, context?: Record<string, unknown>) =>
    post<{ answer: string; generated_by: string }>('/api/assistant', { mode, text, context }),
  analyzeImage: (image_b64: string, mime: string) =>
    post<{ text: string; generated_by: string }>('/api/analyze-image', { image_b64, mime }),
  fx: (base = 'INR') => get<import('./types').FXData>(`/api/fx?base=${base}`),
  fxConvert: (amount: number, from_currency: string, to_currency: string) =>
    post<{ amount: number; from: string; to: string; result: number | null }>('/api/fx/convert', { amount, from_currency, to_currency }),
  recap: () => get<{ text: string; generated_by: string; data_mode: string }>('/api/recap'),
  dictionary: (q = '', category = '') =>
    get<{ count: number; terms: import('./types').DictionaryTerm[] }>(`/api/dictionary?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}`),
  methodology: () => get<import('./types').Methodology>('/api/methodology'),
  demoToggle: (enabled: boolean) => post<{ demo_mode: boolean }>('/api/demo/toggle', { enabled }),
}

export const DISCLAIMER = 'Educational information — not investment advice.'
