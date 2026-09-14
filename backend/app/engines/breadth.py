"""Market breadth: how broad is the current move across all assets?"""

from __future__ import annotations

from typing import Any


def compute_breadth(asset_states: list[dict[str, Any]]) -> dict[str, Any]:
    """asset_states: [{available, change_pct, above_sma50, region, category}]"""
    usable = [a for a in asset_states if a.get("available") and a.get("change_pct") is not None
              and a.get("category") != "volatility"]
    if not usable:
        return {"available": False, "reason": "no data"}

    advancers = sum(1 for a in usable if a["change_pct"] > 0)
    decliners = sum(1 for a in usable if a["change_pct"] < 0)
    above_sma50 = sum(1 for a in usable if a.get("above_sma50"))
    return {
        "available": True,
        "assets_counted": len(usable),
        "advancers": advancers,
        "decliners": decliners,
        "advance_decline_ratio": round(advancers / decliners, 2) if decliners else None,
        "pct_above_sma50": round(above_sma50 / len(usable) * 100, 1),
        "avg_day_change_pct": round(sum(a["change_pct"] for a in usable) / len(usable), 2),
        "meaning": ("broad participation" if above_sma50 / len(usable) > 0.6
                    else "mixed participation" if above_sma50 / len(usable) > 0.4
                    else "narrow participation"),
    }
