# AGENTS.md — standing instructions for coding agents

MarketPulse is a FastAPI + React/Vite monorepo for AI-assisted Indian-market
literacy (NSE-first). Keep edits small and typed; run `pytest` (backend) and
`tsc -b --noEmit` (frontend) before finishing.

## PRISM tracing (do not remove)

This project sends traces to PRISM. Env vars: `PRISMTRACE_API_KEY`,
`PRISMTRACE_PROJECT_ID`, `PRISMTRACE_HOST`.

Tracing is currently wired at: backend/app/ai/prism.py, backend/app/ai/gemini_client.py, backend/app/service.py (per-conversation session_id via contextvar — each chat/analysis/recap run forms its own PRISM trajectory)

**Standing rule.** Whenever you add or change an agent, chain, graph, tool,
retriever, or any entry point that calls a model, wire it to PRISM before you
finish. Unwired code is invisible in the dashboard. If you are unsure whether
something is covered, assume it is not and wire it.
