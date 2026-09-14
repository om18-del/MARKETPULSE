"""All-in-Vercel option: serves the FastAPI app as a single serverless function.

Vercel entrypoint for the Python runtime (requires the `api` directory at
repo root and a vercel.json python runtime config). The recommended
production setup is Vercel (frontend) + Render (backend) — see README —
but this lets everything live in one Vercel project if preferred.
Note: serverless cold starts reset the in-process caches; the app handles
that gracefully (re-fetches, then Demo Mode if all providers fail).
"""

from app.main import app  # noqa: F401 — Vercel ASGI entrypoint

handler = app
