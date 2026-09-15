import { useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Activity, BarChart3, BookMarked, BookOpen, FlaskConical, Globe2, Info, Moon, Newspaper, Search, Star, Sun } from 'lucide-react'
import { OverviewPage } from './pages/Overview'
import { AssetDetailPage } from './pages/AssetDetail'
import { ComparePage } from './pages/Compare'
import { FXPage } from './pages/FX'
import { NewsPage } from './pages/News'
import { ChatPage } from './pages/Chat'
import { LearnPage } from './pages/Learn'
import { DictionaryPage } from './pages/Dictionary'
import { MethodologyPage } from './pages/Methodology'
import { AboutPage } from './pages/About'
import { WatchlistPage } from './pages/WatchlistPage'
import { PulseAssistant } from './components/PulseAssistant'
import { OnboardingTour } from './components/OnboardingTour'
import { SearchBar } from './components/SearchBar'
import { DisclaimerBar, DisclaimerModal } from './components/Disclaimer'
import { ErrorBoundary } from './components/ErrorBoundary'

const NAV = [
  { to: '/', label: 'Overview', icon: Globe2 },
  { to: '/watchlist', label: 'Watchlist', icon: Star },
  { to: '/fx', label: 'FX', icon: BarChart3 },
  { to: '/news', label: 'News', icon: Newspaper },
  { to: '/chat', label: 'Chat', icon: Activity },
  { to: '/learn', label: 'Learn', icon: BookOpen },
  { to: '/dictionary', label: 'Dictionary', icon: BookMarked },
  { to: '/methodology', label: 'Methodology', icon: FlaskConical },
  { to: '/about', label: 'About', icon: Info },
]

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('marketpulse.theme') as 'dark' | 'light') ?? 'dark',
  )
  const [explainText, setExplainText] = useState<string | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const location = useLocation()

  // Close the search overlay whenever the user navigates to an asset.
  useEffect(() => {
    setSearchOpen(false)
  }, [location.pathname])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('marketpulse.theme', theme)
  }, [theme])

  // PA explain channel: pages call onExplain(text)
  useEffect(() => {
    if (!explainText) return
    window.dispatchEvent(new CustomEvent('mp:explain', { detail: explainText }))
    setExplainText(null)
  }, [explainText])

  return (
    <div className="app-bg">
      <DisclaimerModal />
      <DisclaimerBar />
      <nav className="navbar">
        <div className="nav-inner">
          <Link to="/" className="brand">
            <span className="brand-pulse"><Activity size={17} /></span>
            MarketPulse
          </Link>
          <div className="nav-links">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                {n.label}
              </NavLink>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              className="theme-btn"
              onClick={() => setSearchOpen((v) => !v)}
              aria-label="Search stocks"
              title="Search (Ctrl K)"
            >
              <Search size={15} />
            </button>
            <button
              className="theme-btn"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Moon size={15} /> : <Sun size={15} />}
            </button>
          </div>
        </div>
      </nav>

      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname}
          className="shell"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22 }}
        >
          <ErrorBoundary name="Page">
            <Routes location={location}>
              <Route path="/" element={<OverviewPage onExplain={setExplainText} />} />
              <Route path="/asset/:id" element={<AssetDetailPage onExplain={setExplainText} />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/fx" element={<FXPage onExplain={setExplainText} />} />
              <Route path="/news" element={<NewsPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/learn" element={<LearnPage />} />
              <Route path="/dictionary" element={<DictionaryPage onExplain={setExplainText} />} />
              <Route path="/methodology" element={<MethodologyPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="*" element={<OverviewPage onExplain={setExplainText} />} />
            </Routes>
          </ErrorBoundary>
        </motion.main>
      </AnimatePresence>

      {searchOpen && (
        <div
          onClick={() => setSearchOpen(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 180, background: 'rgba(4,8,16,0.6)',
            display: 'flex', justifyContent: 'center', alignItems: 'flex-start',
            padding: '12vh 16px 0', backdropFilter: 'blur(3px)',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: '100%', maxWidth: 560 }}
          >
            <SearchBar autoFocus />
          </div>
        </div>
      )}
      <PulseAssistant />
      <OnboardingTour />
    </div>
  )
}
