"""Dictionary service: load terms.json once, expose search + categories."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

TERMS_PATH = Path(__file__).parent / "terms.json"


@lru_cache
def load_terms() -> list[dict[str, Any]]:
    with open(TERMS_PATH, encoding="utf-8") as f:
        return json.load(f)


def categories() -> list[str]:
    return sorted({t["category"] for t in load_terms()})


def search(q: str = "", category: str = "") -> dict[str, Any]:
    terms = load_terms()
    if category:
        terms = [t for t in terms if t["category"].lower() == category.lower()]
    if q:
        ql = q.lower()
        terms = [t for t in terms if ql in t["term"].lower() or ql in t["definition"].lower()]
    return {"count": len(terms), "terms": terms}
