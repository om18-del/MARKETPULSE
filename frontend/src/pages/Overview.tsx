import { useMemo, useState } from 'react'
import { Flame, Globe2, IndianRupee, LayoutGrid, Search as SearchIcon, TrendingDown, TrendingUp } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api'
import type { GridEntry, Overview } from '../types'
import { RegimeGauge } from '../components/Verdict'
import { IndexCard } from '../components/IndexCard'
import { Heatmap } from '../components/Heatmap'
import { GridSkeleton, CardSkeleton } from '../components/Skeletons'
import { SearchBar } from '../components/SearchBar'
import { RecapCard } from '../components/RecapCard'
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

export function OverviewPage({ onExplain }: { onExplain: (t: string) => void }) {
  const { data, loading, error, refetch } = useApi<Overview>('/api/overview')
  const watchlist = useWatchlist()
  const [showSearch, setShowSearch] = useState(true)

  const watchEntries = useMemo<GridEntry[]>(() => {
    if (!data) return []
    const all = Object.values(data.grid).flat()
    return watchlist.items.map((id) => all.find((e) => e.id === id)).filter(Boolean) as GridEntry[]
  }, [data, watchlist.items])

  if (error) {
    return (
      <div className="err-box" style={{ marginTop: 30 }}>
        <span>Couldn't reach the data engine: {error}</span>
        <button className="btn" onClick={refetch}>Retry</button>
      </div>
    )
  }

  return (
    <div>
      {/* New here? — three-step guide */}
      <section className="section" style={{ marginTop: 22 }}>
        <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14, borderColor: 'color-mix(in srgb, var(--accent-a) 25%, var(--card-border))' }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--accent-a)', marginBottom: 4 }}>1 · Read the pulse</div>
            <div className="faint" style={{ fontSize: 12.5 }}>India-first: NIFTY, Sensex and the NSE universe lead the read. The gauge blends them with global signals — computed by math, explained by AI.</div>
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--accent-a)', marginBottom: 4 }}>2 · Search anything</div>
            <div className="faint" style={{ fontSize: 12.5 }}>Press <kbd>Ctrl</kbd> <kbd>K</kbd> or use the search bar — every result opens the full overview: chart, verdict, evidence, AI thesis and news.</div>
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--accent-a)', marginBottom: 4 }}>3 · Demand the why</div>
            <div className="faint" style={{ fontSize: 12.5 }}>Every verdict shows its factor table, weights and score equation. Select any text → the Pulse Assistant explains it simply. Never advice — always evidence.</div>
          </div>
        </div>
      </section>

      {/* Hero: the general market verdict */}
      <section className="section" style={{ marginTop: 22 }}>
        <div className="card" style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 340px) 1fr', gap: 26, alignItems: 'center', overflow: 'hidden', position: 'relative' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(600px 200px at 20% 0%, rgba(34,211,238,0.07), transparent 60%)', pointerEvents: 'none' }} />
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
              <div style={{ position: 'relative' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                  <Globe2 size={16} style={{ color: 'var(--accent-a)' }} />
                  <h1 style={{ margin: 0, fontSize: 21 }}>Today's global market read</h1>
                  <span className={`chip ${data.data_mode === 'demo' ? 'demo' : 'pos'}`} style={{ marginLeft: 'auto' }}>
                    {data.data_mode === 'demo' ? 'DEMO DATA' : <><span className="updated-dot" /> live</>}
                  </span>
                </div>
                <p className="muted" style={{ fontSize: 14, marginTop: 0 }}>
                  Blended from <b>{data.global.assets_used ?? '—'}</b> instruments across US, India, Europe,
                  Asia-Pacific, commodities and FX. {data.global.vix_score_0_100 != null
                    ? `Volatility sits at ${Math.round(data.global.vix_score_0_100)}/100 on the same scale.`
                    : ''}{' '}
                  The full evidence — every factor, weight and rule — is one click away on each asset.
                </p>
                {data.breadth.available ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginTop: 14 }}>
                    <div className="card" style={{ padding: '10px 13px' }}>
                      <div className="faint">Above 50-day avg</div>
                      <div className="num" style={{ fontSize: 19, fontWeight: 700 }}>{data.breadth.pct_above_sma50}%</div>
                      <div className="faint">{data.breadth.meaning}</div>
                    </div>
                    <div className="card" style={{ padding: '10px 13px' }}>
                      <div className="faint">Advancers / Decliners</div>
                      <div className="num" style={{ fontSize: 19, fontWeight: 700 }}>
                        <span style={{ color: 'var(--pos)' }}>{data.breadth.advancers}</span>
                        <span className="faint"> / </span>
                        <span style={{ color: 'var(--neg)' }}>{data.breadth.decliners}</span>
                      </div>
                      <div className="faint">across {data.breadth.assets_counted} assets</div>
                    </div>
                    <div className="card" style={{ padding: '10px 13px' }}>
                      <div className="faint">Avg day move</div>
                      <div className="num" style={{ fontSize: 19, fontWeight: 700 }}>
                        {((data.breadth.avg_day_change_pct ?? 0) >= 0 ? '+' : '') + (data.breadth.avg_day_change_pct ?? 0).toFixed(2)}%
                      </div>
                      <div className="faint">{data.vix ? `VIX ${data.vix.price.toFixed(1)} (${data.vix.change_pct >= 0 ? '+' : ''}${data.vix.change_pct}%)` : ''}</div>
                    </div>
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      </section>

      {/* Search */}
      <section className="section">
        {showSearch ? (
          <SearchBar />
        ) : (
          <button className="btn" onClick={() => setShowSearch(true)}><SearchIcon size={15} /> Search stocks & indices</button>
        )}
        <div className="faint" style={{ textAlign: 'center', marginTop: 8 }}>
          press <kbd>Ctrl</kbd> <kbd>K</kbd> anywhere to search · every NSE-listed company is searchable · amounts default to ₹ INR
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
              {entries.map((e, i) => (
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
            <Heatmap data={data.heatmap} />
          </div>
          <div>
            <div className="card" style={{ marginBottom: 14 }}>
              <div className="card-title" style={{ color: 'var(--pos)' }}><TrendingUp size={15} /> Top gainers today</div>
              {data.movers.gainers.slice(0, 4).map((e) => (
                <MoverRow key={e.id} e={e} />
              ))}
            </div>
            <div className="card">
              <div className="card-title" style={{ color: 'var(--neg)' }}><TrendingDown size={15} /> Top losers today</div>
              {data.movers.losers.slice(0, 4).map((e) => (
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
