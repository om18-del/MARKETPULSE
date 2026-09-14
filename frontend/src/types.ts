/** Shared API payload types (loose/optional-friendly to tolerate provider variance). */

export type Verdict = 'bullish' | 'bearish' | 'neutral' | 'uncertain'

export interface Instrument {
  id: string
  name: string
  category: string
  region: string
  currency: string
  weight?: number
  fx_pair?: boolean
}

export interface GlobalRead {
  available: boolean
  verdict?: Verdict
  score_0_100?: number
  confidence?: number
  assets_used?: number
  vix_score_0_100?: number | null
  equation?: string
  reason?: string
  disclaimer?: string
}

export interface GridEntry {
  id: string
  name: string
  category: string
  region: string
  currency: string
  available?: boolean
  price?: number
  change_pct?: number
  spark?: number[]
  verdict?: Verdict
  score?: number
  above_sma50?: boolean
  demo?: boolean
}

export interface Breadth {
  available: boolean
  assets_counted?: number
  advancers?: number
  decliners?: number
  pct_above_sma50?: number
  avg_day_change_pct?: number
  meaning?: string
}

export interface Overview {
  global: GlobalRead
  breadth: Breadth
  grid: Record<string, GridEntry[]>
  movers: { gainers: GridEntry[]; losers: GridEntry[] }
  heatmap: { id: string; name: string; region: string; category: string; change_pct: number }[]
  vix: { price: number; change_pct: number } | null
  data_mode: 'live' | 'demo'
  disclaimer: string
}

export interface FactorPart {
  name: string
  value: string
  rule: string
  weight: number
  sub_score: number
  meaning: string
}

export interface Assessment {
  available: boolean
  reason?: string
  instrument_name?: string
  verdict?: Verdict
  score_0_100?: number
  confidence?: number
  equation?: string
  factors?: {
    trend: { score: number; parts: FactorPart[] }
    momentum: { score: number; parts: FactorPart[] }
    volatility: { score: number; parts: FactorPart[]; realized_vol?: number | null }
    volume: { score: number; parts: FactorPart[] }
    news: { score: number; applied: boolean; meaning: string }
  }
  weights?: Record<string, number>
  what_would_change_this_read?: string[]
  disclaimer?: string
}

export interface FilterBundle {
  vwap: { vwap: number; zscore: number; band: string; rule: string } | null
  volume_pressure: { updown_ratio: number | null; obv_slope: number | null; volume_zscore: number | null; proxy_label: string; rule: string } | null
  vix_velocity: { change_5d: number; change_pct_5d: number; zscore: number; regime: string; rule: string } | null
}

export interface NewsArticle {
  title: string
  link: string
  publisher: string
  published: string
  sentiment?: number
  reason?: string
  key_phrase?: string
  method?: string
}

export interface Analysis {
  available: boolean
  instrument: Instrument
  data_mode: 'live' | 'demo'
  assessment: Assessment
  filters: FilterBundle
  cross_asset: { drivers: Record<string, { correlation: number; lead5d_agreement: number | null; d5_change_pct: number }>; summary: string }
  news: { topic: string; aggregate_score: number; method: string; articles: NewsArticle[] }
  thesis: { text: string; generated_by: string }
  disclaimer: string
}

export interface AssetDetail {
  instrument: Instrument
  quote: { price: number; change_pct: number; provider: string; demo: boolean } | null
  rows: { date: string; open: number | null; high: number | null; low: number | null; close: number; volume: number | null }[]
  spark: number[]
  data_mode: 'live' | 'demo'
  provenance: { provider: string; fetched_at?: string; attempts?: unknown[] }
  disclaimer: string
}

export interface FXData {
  currencies: string[]
  flags: Record<string, string>
  usd_rates: Record<string, number | null>
  pairs: Record<string, { name: string; rate_usd: number; d1_pct: number; d5_pct: number; spark: number[]; demo: boolean }>
  data_mode: 'live' | 'demo'
  selected_base?: string
  disclaimer: string
}

export interface DictionaryTerm {
  term: string
  category: string
  definition: string
  see_also?: string[]
}

export interface Methodology {
  title: string
  philosophy: string[]
  regime_model: {
    description: string
    scale: string
    weights: Record<string, number>
    why_these_weights: string
    verdict_mapping: Record<string, string>
    confidence: string
  }
  indicators: { name: string; origin: string; what: string; why: string; rule_in_app?: string }[]
  honesty_notes: string[]
  ai_separation: { analysis_engine: string; pulse_assistant: string; shared_rule: string }
}
