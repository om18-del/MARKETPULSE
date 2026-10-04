import { useCallback, useMemo, useState } from 'react'
import { Activity, Flame, FlaskConical, Globe2, IndianRupee, LayoutGrid, Search as SearchIcon, TrendingDown, TrendingUp } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api'
import type { GridEntry, Overview } from '../types'
import { RegimeGauge } from '../components/Verdict'
import { IndexCard } from '../components/IndexCard'
import { Heatmap } from '../components/Heatmap'
import { GridSkeleton, CardSkeleton } from '../components/Skeletons'
import { SearchBar } from '../components/SearchBar'
import { RecapCard } from '../components/RecapCard'
import { ScannerPanel } from '../components/ScannerPanel'
import { CurrencyPanel } from '../components/CurrencyPanel'
import { useWatchlist } from '../hooks/useWatchlist'
import { useEffect } from 'react'

interface NseMover { symbol: string; name: string; last_price: number; change_pct: number }
interface NseMoversData {
  available: boolean
  gainers?: NseMover[]
  losers?: NseMover[]
  advances?: number | null
  declines?: number | null
  counted?: number
  reason?: string
}

const REGION_LABEL: Record<string, string> = {
  us: '🇺🇸 United States',
  india: '🇮🇳 India',
  europe: '🇪🇺 Europe',
  apac: '🌏 Asia-Pacific',
  macro: '🧭 Macro & Commodities',
  fx: '💱 Currencies',
}

type LiveQuote = { price: number; change_pct: number; data_date?: string; symbol: string }

export function OverviewPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { data, loading, error, refetch } = useApi<Overview>('/api/overview')
  const watchlist = useWatchlist()
  const [showSearch, setShowSearch] = useState(true)
  const snapshotDate = new Intl.DateTimeFormat('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date())

  // Real-time overlay: the overview grid is built on EOD history; this
  // endpoint returns the exchange's live quotes and we merge them over the
  // cards every 60s so displayed values tick during market hours.
  const [live, setLive] = useState<Record<string, LiveQuote>>({})
  const [liveStamp, setLiveStamp] = useState<Date | null>(null)
  useEffect(() => {
    let cancelled = false
    const pull = async () => {
      try {
        const r = await fetch('/api/live-quotes')
        if (!r.ok) return
        const j = await r.json()
        if (!cancelled && j.quotes) {
          setLive(j.quotes)
          setLiveStamp(new Date())
        }
      } catch {
        /* keep last good overlay */
      }
    }
    void pull()
    const iv = setInterval(() => {
      if (document.visibilityState === 'visible') void pull()
    }, 60_000)
    return () => {
      cancelled = true
      clearInterval(iv)
    }
  }, [])

  const applyLive = useCallback(
    (entries: GridEntry[]) =>
      entries.map((e) => {
        const q = live[e.id]
        return q && e.price != null
          ? { ...e, price: q.price, change_pct: q.change_pct }
          : e
      }),
    [live],
  )

  const applyLiveHeat = useCallback(
    (rows: { id: string; name: string; region: string; category: string; change_pct: number }[]) =>
      rows.map((r) => {
        const q = live[r.id]
        return q ? { ...r, change_pct: q.change_pct } : r
      }),
    [live],
  )

  const watchEntries = useMemo<GridEntry[]>(() => {
    if (!data) return []
    const all = Object.values(data.grid).flat()
    return applyLive(watchlist.items.map((id) => all.find((e) => e.id === id)).filter(Boolean) as GridEntry[])
  }, [data, watchlist.items, applyLive])

  if (error) {
    return (
      <div className="err-box" style={{ marginTop: 30 }}>
        <span>Couldn't reach the data engine: {error}</span>
        <button className="btn" onClick={refetch}>Retry</button>
      </div>
    )
  }

  return (
    <div className="market-overview">
      <header className="overview-heading">
        <div>
          <div className="overview-eyebrow"><span className="overview-eyebrow-dot" /> MARKET INTELLIGENCE <span className="overview-eyebrow-divider">/</span> GLOBAL + NSE</div>
          <h1>Market overview</h1>
          <p>A clearer read on what’s moving — and the signals behind it.</p>
        </div>
        <div className="overview-date">
          <span className="overview-date-icon"><Activity size={15} /></span>
          <span><small>MARKET SNAPSHOT</small><strong>{snapshotDate}</strong></span>
        </div>
      </header>

      {/* Hero: the general market verdict */}
      <section className="section overview-hero-section">
        <div className="card overview-hero">
          {loading && !data ? (
            <>
              <CardSkeleton height={210} />
              <div>
                <CardSkeleton height={40} />
                <div style={{ height: 14 }} />
                <CardSkeleton height={110} />
              </div>
            </>
          ) : data ? (
            <>
              <RegimeGauge
                verdict={data.global.verdict}
                score={data.global.score_0_100}
                confidence={data.global.confidence}
              />
              <div className="overview-hero-copy">
                <div className="overview-hero-top">
                  <span className="overview-hero-mark"><Globe2 size={17} /></span>
                  <div className="overview-hero-heading">
                    <span className="overview-hero-eyebrow">GLOBAL REGIME</span>
                    <h2>Today’s global market read</h2>
                  </div>
                  <span className={`chip ${data.data_mode === 'demo' ? 'demo' : 'pos'}`} style={{ marginLeft: 'auto' }}>
                    {data.data_mode === 'demo' ? 'DEMO DATA' : <><span className="updated-dot" /> live</>}
                  </span>
                </div>
                <p className="muted overview-summary">
                  Blended from <b>{data.global.assets_used ?? '—'}</b> instruments across US, India, Europe,
                  Asia-Pacific, commodities and FX. {data.global.vix_score_0_100 != null
                    ? `Volatility sits at ${Math.round(data.global.vix_score_0_100)}/100 on the same scale.`
                    : ''}{' '}
                  Explore the evidence behind each asset’s read.
                </p>
                {data.breadth.available ? (
                  <div className="overview-stats">
                    <div className="card overview-stat">
                      <div className="overview-stat-label">Above 50-day average</div>
                      <div className="overview-stat-value num">{data.breadth.pct_above_sma50}%</div>
                      <div className="overview-stat-note">{data.breadth.meaning}</div>
                    </div>
                    <div className="card overview-stat">
                      <div className="overview-stat-label">Advancers / decliners</div>
                      <div className="overview-stat-value num">
                        <span style={{ color: 'var(--pos)' }}>{data.breadth.advancers}</span>
                        <span className="faint"> / </span>
                        <span style={{ color: 'var(--neg)' }}>{data.breadth.decliners}</span>
                      </div>
                      <div className="overview-stat-note">Across {data.breadth.assets_counted} assets</div>
                    </div>
                    <div className="card overview-stat">
                      <div className="overview-stat-label">Average day move</div>
                      <div className="overview-stat-value num">
                        {((data.breadth.avg_day_change_pct ?? 0) >= 0 ? '+' : '') + (data.breadth.avg_day_change_pct ?? 0).toFixed(2)}%
                      </div>
                      <div className="overview-stat-note">{data.vix ? `VIX ${data.vix.price.toFixed(1)} (${data.vix.change_pct >= 0 ? '+' : ''}${data.vix.change_pct}%)` : 'Across tracked markets'}</div>
                    </div>
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      </section>

      <section className="section orientation-section" aria-label="How to read MarketPulse">
        <div className="card orientation-card">
          <div className="orientation-intro">
            <span className="orientation-icon"><FlaskConical size={17} /></span>
            <span><strong>Built for clarity</strong><small>Math first. Evidence always.</small></span>
          </div>
          <div className="orientation-point">
            <span className="orientation-number">01</span>
            <span><strong>Read the pulse</strong><small>Global signals + Indian breadth</small></span>
          </div>
          <div className="orientation-point">
            <span className="orientation-number">02</span>
            <span><strong>Search any instrument</strong><small>From NIFTY to NSE listings</small></span>
          </div>
          <div className="orientation-point">
            <span className="orientation-number">03</span>
            <span><strong>See the “why”</strong><small>Every read comes with evidence</small></span>
          </div>
        </div>
      </section>

      {/* Search */}
      <section className="section overview-search-section">
        {showSearch ? (
          <SearchBar />
        ) : (
          <button className="btn" onClick={() => setShowSearch(true)}><SearchIcon size={15} /> Search stocks & indices</button>
        )}
        <div className="faint" style={{ textAlign: 'center', marginTop: 8 }}>
          press <kbd>Ctrl</kbd> <kbd>K</kbd> anywhere to search · every NSE-listed company is searchable · amounts default to ₹ INR
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 4 }}>
          {liveStamp ? (
            <span className="chip pos" title="All prices refresh automatically every minute during market hours">
              <span className="live-dot" /> live prices · updated {liveStamp.toLocaleTimeString()}
            </span>
          ) : (
            <span className="chip">loading live prices…</span>
          )}
        </div>
      </section>

      {/* Live NSE movers — direct from nseindia.com */}
      <NseMoversCard />

      {/* Watchlist */}
      {watchEntries.length ? (
        <section className="section">
          <h2 className="card-title" style={{ fontSize: 15 }}><TrendingUp size={15} /> Your watchlist</h2>
          <div className="grid cols-4">
            {watchEntries.map((e, i) => (
              <IndexCard key={e.id} e={e} index={i} watched onToggleWatch={watchlist.toggle} />
            ))}
          </div>
        </section>
      ) : null}

      {/* Trend grid by region */}
      {loading && !data ? (
        <section className="section"><GridSkeleton count={8} /></section>
      ) : data ? (
        Object.entries(data.grid).map(([region, entries]) => (
          <section className="section" key={region}>
            <h2 className="card-title" style={{ fontSize: 15 }}>
              <LayoutGrid size={15} /> {REGION_LABEL[region] ?? region}
              <span className="faint" style={{ textTransform: 'none', letterSpacing: 0 }}>{entries.filter((e) => e.available !== false).length} assets</span>
            </h2>
            <div className="grid cols-4">
              {applyLive(entries).map((e, i) => (
                <IndexCard key={e.id} e={e} index={i} watched={watchlist.has(e.id)} onToggleWatch={watchlist.toggle} />
              ))}
            </div>
          </section>
        ))
      ) : null}

      {/* Heatmap + movers */}
      {data ? (
        <section className="section grid cols-2" style={{ alignItems: 'start' }}>
          <div className="card">
            <div className="card-title"><Flame size={15} /> Market heatmap <span className="faint" style={{ textTransform: 'none' }}>day change %</span></div>
            <Heatmap data={applyLiveHeat(data.heatmap)} />
          </div>
          <div>
            <div className="card" style={{ marginBottom: 14 }}>
              <div className="card-title" style={{ color: 'var(--pos)' }}><TrendingUp size={15} /> Top gainers today</div>
              {applyLive(data.movers.gainers).slice(0, 4).map((e) => (
                <MoverRow key={e.id} e={e} />
              ))}
            </div>
            <div className="card">
              <div className="card-title" style={{ color: 'var(--neg)' }}><TrendingDown size={15} /> Top losers today</div>
              {applyLive(data.movers.losers).slice(0, 4).map((e) => (
                <MoverRow key={e.id} e={e} />
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {/* Recap */}
      <section className="section">
        <RecapCard />
      </section>

      {/* Intraday ⟷ trend conflict scanner (reversal candidates) */}
      <ScannerPanel />

      {/* Currency panel */}
      {data ? (
        <section className="section">
          <CurrencyPanelWrapper onExplain={onExplain} />
        </section>
      ) : null}

      <p className="faint" style={{ textAlign: 'center', marginTop: 30 }}>{data?.disclaimer ?? 'Educational information — not investment advice.'}</p>
    </div>
  )
}

function MoverRow({ e }: { e: GridEntry }) {
  const up = (e.change_pct ?? 0) >= 0
  return (
    <a href={`/asset/${e.id}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--card-border)', fontSize: 13.5 }}>
      <span style={{ fontWeight: 600 }}>{e.name}</span>
      <span className="num" style={{ color: up ? 'var(--pos)' : 'var(--neg)', fontWeight: 700 }}>
        {up ? '+' : ''}{(e.change_pct ?? 0).toFixed(2)}%
      </span>
    </a>
  )
}

/** Live NIFTY 50 gainers/losers straight from nseindia.com (keyless).
 *  Hidden entirely if NSE is unreachable — no fake rows. */
function NseMoversCard() {
  const [data, setData] = useState<NseMoversData | null>(null)
  useEffect(() => {
    let alive = true
    api.nseMovers().then((d) => { if (alive) setData(d) }).catch(() => {})
    const t = setInterval(() => {
      api.nseMovers().then((d) => { if (alive) setData(d) }).catch(() => {})
    }, 120_000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  if (!data?.available || !data.gainers?.length || !data.losers?.length) return null
  return (
    <section className="section">
      <div className="card">
        <div className="card-title">
          <IndianRupee size={15} /> NIFTY 50 — live from NSE
          <span className="faint" style={{ textTransform: 'none', letterSpacing: 0 }}>
            {data.counted} stocks · {data.advances ?? '—'} advancing / {data.declines ?? '—'} declining
          </span>
          <span className="chip pos" style={{ marginLeft: 'auto' }}>direct · nseindia.com</span>
        </div>
        <div className="grid cols-2" style={{ gap: 18 }}>
          <div>
            <div className="faint" style={{ fontSize: 12, marginBottom: 4, color: 'var(--pos)', fontWeight: 700 }}>TOP GAINERS</div>
            {data.gainers.map((m) => <NseMoverRow key={m.symbol} m={m} />)}
          </div>
          <div>
            <div className="faint" style={{ fontSize: 12, marginBottom: 4, color: 'var(--neg)', fontWeight: 700 }}>TOP LOSERS</div>
            {data.losers.map((m) => <NseMoverRow key={m.symbol} m={m} />)}
          </div>
        </div>
      </div>
    </section>
  )
}

function NseMoverRow({ m }: { m: NseMover }) {
  const up = m.change_pct >= 0
  return (
    <a href={`/asset/nse-${m.symbol.toLowerCase()}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '7px 0', borderBottom: '1px solid var(--card-border)', fontSize: 13.5 }}>
      <span><b>{m.symbol}</b> <span className="faint" style={{ fontSize: 12 }}>{m.name.length > 34 ? `${m.name.slice(0, 34)}…` : m.name}</span></span>
      <span style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
        <span className="num">₹{m.last_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
        <span className="num" style={{ color: up ? 'var(--pos)' : 'var(--neg)', fontWeight: 700, minWidth: 58, textAlign: 'right' }}>
          {up ? '+' : ''}{m.change_pct.toFixed(2)}%
        </span>
      </span>
    </a>
  )
}

function CurrencyPanelWrapper({ onExplain }: { onExplain: (t: string) => void }) {
  const { data: fx } = useApi<import('../types').FXData>('/api/fx?base=USD')
  if (!fx) return <CardSkeleton height={260} />
  return <CurrencyPanel fx={fx} onExplain={onExplain} />
}
