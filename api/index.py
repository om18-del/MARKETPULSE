"""All-in-Vercel option: serves the FastAPI app as a single serverless function.

Vercel entrypoint for the Python runtime (api/index.py auto-detects; deps from
api/requirements.txt; backend/ is added to sys.path below). The recommended
production setup is Vercel (frontend) + Render (backend) — see README — but
this lets everything live in one Vercel project if preferred.

Serverless notes:
- Cold starts reset the in-process caches; the app re-fetches gracefully and
  only falls back to clearly-labeled Demo Mode if every provider fails.
- Secrets come from Vercel env vars (GEMINI_API_KEY, PRISMTRACE_*, ...) —
  never a .env file.
"""

import sys
from pathlib import Path

# The FastAPI package lives in backend/; make it importable in the function.
_BACKEND = str(Path(__file__).resolve().parent.parent / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.main import app  # noqa: E402,F401 — Vercel ASGI entrypoint

handler = app
