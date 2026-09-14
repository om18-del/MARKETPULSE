"""Stooq — keyless primary provider (CSV daily history).

Endpoint: https://stooq.com/q/d/l/?s=<symbol>&i=d
Returns CSV: Date,Open,High,Low,Close,Volume
Symbols: lowercase; indices with '^' prefix; US stocks suffixed '.us';
Indian stocks '.in'; FX pairs like 'usdinr'; commodities 'xauusd', 'cl.f'.
Note: Stooq occasionally renames index symbols (e.g. ^spx -> ^usl20);
the registry holds the current known-good mapping.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re

from .base import ProviderError, client

BASE_URL = "https://stooq.com/q/d/l/"


def _solve_pow(challenge: str, difficulty: int) -> int:
    """Solve Stooq's browser proof-of-work exactly like a browser would:
    find n such that sha256(challenge + str(n)) starts with `difficulty` zeros."""
    target = "0" * difficulty
    n = 0
    while True:
        if hashlib.sha256(f"{challenge}{n}".encode()).hexdigest().startswith(target):
            return n
        n += 1


class StooqProvider:
    name = "stooq"

    async def fetch_history(self, symbol: str) -> list[dict]:
        url = f"{BASE_URL}?s={symbol}&i=d"
        try:
            async with client() as http:
                resp = await http.get(url)
                text = resp.text.strip()

                # Transparent browser-equivalent gate handling (JavaScript PoW)
                if "__verify" in text and "<" in text[:200].lower():
                    m_c = re.search(r'c="([^"]+)"', text)
                    m_d = re.search(r",d=(\d+)", text)
                    if m_c and m_d:
                        n = _solve_pow(m_c.group(1), int(m_d.group(1)))
                        v = await http.post(
                            "https://stooq.com/__verify",
                            content=f"c={m_c.group(1)}&n={n}",
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                        )
                        if v.status_code == 200:
                            resp = await http.get(url)
                            text = resp.text.strip()
        except Exception as exc:  # network layer
            raise ProviderError(f"stooq network error: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"stooq HTTP {resp.status_code}")
        if not text or text.lower().startswith("no data") or text.lower().startswith("access denied"):
            raise ProviderError("stooq: no data for symbol (possibly IP-gated)")
        if "<html" in text[:200].lower():
            # Unsolvable gate / block page — treat as failure so fallbacks kick in
            raise ProviderError("stooq: blocked or rate-limited (html response)")

        rows: list[dict] = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                rows.append({
                    "date": (row.get("Date") or row.get("date") or "").strip(),
                    "open": row.get("Open") or row.get("open"),
                    "high": row.get("High") or row.get("high"),
                    "low": row.get("Low") or row.get("low"),
                    "close": row.get("Close") or row.get("close"),
                    "volume": row.get("Volume") or row.get("volume") or 0,
                })
        except Exception as exc:
            raise ProviderError(f"stooq parse error: {exc}") from exc

        if not rows:
            raise ProviderError("stooq: empty csv")
        return rows
