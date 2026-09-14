# 📊 MarketPulse — AI Market Decision-Support Platform

**See the market's pulse. Understand the why.**

MarketPulse brings scattered market signals — prices, volatility, FX, commodities, news — into one explainable view for beginners. It tells you whether the current market environment looks **Bullish · Bearish · Neutral · Uncertain**, shows **the full evidence behind every number**, and never gives investment advice.

> ⚖️ **Educational information — not investment advice.** MarketPulse is not a trading bot, issues no buy/sell signals, and makes no price predictions. Every verdict is a snapshot of the *current* environment, shown with its evidence.

---

## ✨ What's inside

| Area | Details |
|---|---|
| **Global Overview (homepage)** | Animated regime gauge (aggregate verdict + confidence), market breadth (above-50-DMA %, advancers/decliners), regional trend grid with sparklines, market heatmap, top movers, daily 60-second recap |
| **Universal Search** | Any of 38 instruments (indices, stocks, FX, commodities) — autocomplete, keyboard nav, `Ctrl/⌘ + K` anywhere |
| **Asset Deep-Dive** | Price chart, regime verdict, **Evidence panel** (factor table: value + rule + contribution per factor), deterministic filters, AI thesis, related news with sentiment citations, image analysis |
| **Two separated AI roles** | **Analysis Engine** — data-grounded theses + chat (never invents numbers, never advises). **Pulse Assistant** — explains any *selected text* in simple words + light general Q&A |
| **Currency Exchange** | Preferred base currency (persisted), live ECB rate grid for 9 currencies, converter, AI explainers |
| **News** | Google News RSS topics with AI sentiment tags + the key phrase behind each tag; deterministic keyword fallback |
| **Learn Hub** | 4 beginner lessons + 10-question quiz with explanations |
| **Dictionary** | 50 searchable terms with plain-English definitions and "explain simpler" via PA |
| **Methodology page** | Every indicator's origin (RSI — Wilder 1978…), in-app rule, and regime weights — fully auditable |
| **Voice** | Mic input + read-aloud via free Web Speech API (auto-hides if unsupported) |
| **Resilience** | Provider fallback chain + circuit breakers + caches; auto **Demo Mode** (clearly labeled) if all data fails; AI fallbacks if quota exhausts |
| **Polish** | Dark/light themes, Framer Motion micro-interactions, skeletons, tabular numerals, WCAG-minded, installable PWA |

## 🚀 Quickstart (localhost, 3 commands)

**Prereqs:** Python 3.11+, Node 18+.

```bash
# 1 — Backend (port 8000)
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # Windows
# .venv/bin/pip install -r requirements.txt          # macOS/Linux
cp ../.env.example .env                              # then paste your GEMINI_API_KEY
.venv/Scripts/python -m uvicorn app.main:app --reload

# 2 — Frontend (port 5173) — new terminal
cd frontend
npm install
npm run dev

# 3 — Open http://localhost:5173
```

Works **immediately with zero API keys** (keyless market + FX data). Add a Gemini key to unlock AI theses, assistant, recap and news analysis.

## 🔑 API keys (all free)

| Env var (backend/.env) | Required | Where | Free tier |
|---|---|---|---|
| `GEMINI_API_KEY` | for AI features | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | ~10 RPM / 1500 day |
| `TWELVEDATA_API_KEY` | optional | [twelvedata.com](https://twelvedata.com) | 800/day |
| `FINNHUB_API_KEY` | optional | [finnhub.io](https://finnhub.io) | 60/min |
| `ALPHAVANTAGE_API_KEY` | optional | [alphavantage.co](https://www.alphavantage.co) | 25/day |
| *(Stooq + Frankfurter/ECB)* | **none needed** | — | keyless primaries |

**Data provider chain (no Yahoo):** Stooq (keyless) → Frankfurter/ECB (keyless FX) → Twelve Data → Finnhub → Alpha Vantage. Per-provider circuit breakers; the Evidence panel shows which provider served each number.

## 🧠 How a verdict is reached

```
public data ──► validation ──► deterministic math layer ──► regime engine ──► verdict + evidence
                                   (SMA/RSI/MACD/ATR/vol,     Trend 35% · Momentum 25%
                                    VWAP z-score, VIX          Volatility 25% · Volume 15%
                                    velocity, volume-pressure  News ±10% cap
                                    proxy, cross-asset matrix)
                                          │
                                          ▼
                              Gemini translates features → structured thesis
                              (the model never invents a number)
```

High realized volatility (>28% ann.) pushes reads toward **Uncertain** instead of false confidence. Every verdict lists *"What would change this read"*. Full details: [/api/methodology](http://localhost:8000/api/methodology) or the in-app **Methodology** page.

## 🏗 Architecture

```
MARKETPULSE/
├── backend/                  FastAPI :8000 (lean, no DB)
│   ├── app/core/             config, TTL cache + circuit breakers
│   ├── app/data/             registry (38 instruments) · providers/ (stooq,
│   │                         frankfurter, twelvedata, finnhub, alphavantage)
│   │                         aggregator (fallback chain) · validation
│   ├── app/engines/          indicators · filters · regime · breadth · fx
│   ├── app/news/             rss (Google News) · analyzer (Gemini + keyword fallback)
│   ├── app/ai/               gemini_client · analysis/ (thesis, chat, recap, fx, vision)
│   │                         assistant/ (explain-snippet, general QA, FAQ KB)
│   ├── app/dictionary/       50-term terms.json + service
│   ├── app/demo/             deterministic demo snapshots
│   ├── app/routes/api.py     17 endpoints
│   ├── app/methodology.json  full audit document
│   └── tests/                34 pytest tests
├── frontend/                 React 19 + Vite + TS :5173 (PWA)
│   └── src/pages/            Overview · AssetDetail · Compare · FX · News · Chat
│                             Learn · Dictionary · Methodology · About
│   └── src/components/       RegimeGauge · EvidencePanel · FilterReadout · ThesisCard
│                             PulseAssistant (SelectToExplain) · CurrencyPanel · Heatmap …
├── vercel.json               frontend deploy (Vercel)
├── render.yaml               backend deploy (Render)
└── api/index.py              optional all-in-Vercel serverless entrypoint
```

**API:** `GET /api/overview · /api/search?q= · /api/asset/{id} · /api/analysis/{id} · /api/fx · /api/news?topic= · /api/recap · /api/dictionary · /api/methodology · /api/health` — `POST /api/chat · /api/assistant · /api/analyze-image · /api/fx/convert · /api/demo/toggle`. Interactive docs at `/docs`.

## ☁️ Deploy to the web (free)

**Recommended: Vercel (frontend) + Render (backend)**

1. **Backend → Render:** New → Blueprint → select this repo (uses `render.yaml`). Add env vars: `GEMINI_API_KEY` (+ optional provider keys), set `CORS_ORIGINS` to your Vercel URL. Note the `https://…onrender.com` URL.
2. **Frontend → Vercel:** New Project → import repo → **Root Directory: `frontend`**. Env var: `VITE_API_BASE_URL=https://<your-backend>.onrender.com`. Deploy.
3. Update Render's `CORS_ORIGINS` to include your final Vercel URL → redeploy.

**All-in-Vercel alternative:** `api/index.py` + `vercel.json` ship the FastAPI app as a serverless function (cold starts reset caches — fine for light demos). Add a Python requirements step for the api (`backend/requirements.txt`).

**Honest deployment caveats:** datacenter IPs are sometimes blocked by Stooq's bot-gate (the code handles its proof-of-work challenge transparently, but IP reputation can still deny — then Frankfurter keeps FX live and other keys keep equities live); public traffic can exhaust Gemini's free RPM (caching + keyword fallbacks handle it).

## 🎤 Hackathon demo script (2 minutes)

1. Open `/` → the **global regime gauge** animates in; walk through breadth + one region grid.
2. Click **Generate** on the Daily Recap → read the 60-second market story aloud (or hit 🔊).
3. `Ctrl+K` → type **reliance** → deep-dive: chart, verdict → open **Evidence panel** → expand Trend factors → show the score *equation*.
4. Select one line of the AI thesis → the **"✨ Explain with PA"** chip appears → PA explains it in simple words.
5. Ask the assistant *"what is VWAP?"* — then show the **Dictionary** and **Methodology** pages ("we can audit every number").
6. Open **FX** → switch base to **INR** → converter + rate grid.
7. **Learn** tab → fire one quiz question. Close on the disclaimer: *"It never advises — it explains, with evidence."*

## 🧪 Tests & checks

```bash
cd backend && .venv/Scripts/python -m pytest tests -q     # 34 tests
cd frontend && npx tsc -b --noEmit && npm run build       # typecheck + production build
```

## 🔒 Security notes

- API keys live **only** in `backend/.env` (gitignored) / deployment dashboards — never in the frontend bundle or git.
- CORS is explicit; the AI is prompt-constrained against advice/prediction and every AI output ends with the disclaimer.
- **Rotate your Gemini key after sharing it anywhere** (including chat tools) — takes 30 seconds in AI Studio.

## 📄 License

MIT — see [LICENSE](LICENSE).
