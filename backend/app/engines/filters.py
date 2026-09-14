"""Deterministic filters — the pre-AI mathematical layer.

These compute the LiquidityAI-style features (VWAP z-scores, VIX velocity,
cross-asset pressure, volume pressure) BEFORE any LLM sees data. The LLM
translates them; it never invents them. Every output is a number with a
threshold rule, ready for the Evidence panel.
"""

from __future__ import annotations

from typing import Any, Optional

from . import indicators as ind

Row = dict


def vwap_zscore(rows: list[Row], window: int = 10) -> Optional[dict]:
    """|price - VWAP| / rolling sigma of (price - VWAP): statistical stretch.

    |z| < 1   -> normal; 1-2 -> stretched; >2 -> statistically extended move
    """
    closes = [float(r["close"]) for r in rows]
    if len(rows) < window + 10:
        return None
    diffs: list[float] = []
    for i in range(window, len(rows)):
        vwap = ind.session_vwap(rows[max(0, i - window):i + 1], window)
        if vwap:
            diffs.append(closes[i] - vwap)
    if len(diffs) < 8:
        return None
    cur_vwap = ind.session_vwap(rows, window)
    if not cur_vwap:
        return None
    cur_diff = closes[-1] - cur_vwap
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
    sd = var ** 0.5 or 1e-9
    z = cur_diff / sd
    band = "normal" if abs(z) < 1 else ("stretched" if abs(z) < 2 else "extended")
    return {"vwap": cur_vwap, "zscore": z, "band": band,
            "rule": "|price - 10d VWAP| / rolling sigma; |z|>2 = statistically extended"}


def vix_velocity(vix_rows: list[Row] | None, window: int = 5) -> Optional[dict]:
    """Rate of change + z-score of VIX change: is fear rising *fast*?"""
    if not vix_rows or len(vix_rows) < window + 5:
        return None
    closes = [float(r["close"]) for r in vix_rows]
    changes = [closes[i] - closes[i - window] for i in range(window, len(closes))]
    if not changes:
        return None
    cur_change = changes[-1]
    mean = sum(changes) / len(changes)
    var = sum((c - mean) ** 2 for c in changes) / len(changes)
    sd = var ** 0.5 or 1e-9
    z = (cur_change - mean) / sd
    pct = cur_change / closes[-window - 1] * 100 if closes[-window - 1] else 0
    if z > 1.5 or pct > 15:
        regime = "spiking"
    elif z < -1.5 or pct < -15:
        regime = "collapsing"
    else:
        regime = "stable"
    return {"change_5d": cur_change, "change_pct_5d": pct, "zscore": z, "regime": regime,
            "rule": "5-day VIX change vs its own history; |z|>1.5 = vol regime shift"}


def cross_asset_pressure(
    target_rows: list[Row],
    driver_rows: dict[str, list[Row]],
    lookback: int = 60,
) -> dict:
    """Correlation/lead-lag of macro drivers (DXY, 10Y, gold, crude, VIX, FX)
    onto a target index — the multi-asset interaction loop.

    Returns per-driver: correlation, 5d lead direction agreement, plain label.
    """
    out: dict[str, Any] = {"drivers": {}, "summary": ""}
    t_closes = [float(r["close"]) for r in target_rows[-lookback - 5:]]
    if len(t_closes) < 30:
        out["summary"] = "insufficient history"
        return out
    t_rets = [t_closes[i] / t_closes[i - 1] - 1 for i in range(1, len(t_closes)) if t_closes[i - 1]]

    active = 0
    for name, rows in driver_rows.items():
        d_closes = [float(r["close"]) for r in rows[-lookback - 5:]]
        if len(d_closes) < 30:
            continue
        d_rets = [d_closes[i] / d_closes[i - 1] - 1 for i in range(1, len(d_closes)) if d_closes[i - 1]]
        n = min(len(t_rets), len(d_rets))
        if n < 20:
            continue
        a, b = t_rets[-n:], d_rets[-n:]
        ma, mb = sum(a) / n, sum(b) / n
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
        va = sum((x - ma) ** 2 for x in a) ** 0.5
        vb = sum((x - mb) ** 2 for x in b) ** 0.5
        corr = cov / (va * vb) if va and vb else 0.0
        # 5-day lead agreement: driver's 5d return sign vs target's next-5d sign
        lead_ok = 0
        lead_n = 0
        for lag in range(0, max(1, len(d_rets) - 6)):
            d5 = sum(d_rets[lag:lag + 5])
            t5_next = sum(t_rets[lag + 5:lag + 10])
            if d5 != 0 and t5_next != 0:
                lead_n += 1
                if (d5 > 0) == (t5_next > 0):
                    lead_ok += 1
        lead = (lead_ok / lead_n) if lead_n >= 10 else None
        out["drivers"][name] = {
            "correlation": round(corr, 2),
            "lead5d_agreement": round(lead, 2) if lead is not None else None,
            "d5_change_pct": round((d_closes[-1] / d_closes[-6] - 1) * 100, 2),
        }
        active += 1
    out["summary"] = f"{active} drivers analyzed" if active else "no driver history"
    return out


def volume_pressure(rows: list[Row]) -> Optional[dict]:
    """Institutional-flow *proxy* from public data: up/down volume ratio,
    OBV slope and volume z-score — honestly labeled as a proxy."""
    ratio = ind.updown_volume_ratio(rows)
    slope = ind.obv_slope(rows)
    vols = [float(r.get("volume") or 0) for r in rows]
    z = None
    if len(vols) >= 30 and sum(vols) > 0:
        w = vols[-60:]
        mean = sum(w) / len(w)
        var = sum((v - mean) ** 2 for v in w) / len(w) or 1e-9
        z = (vols[-1] - mean) / (var ** 0.5)
    if ratio is None and slope is None and z is None:
        return None
    label = "balanced"
    if ratio and ratio > 1.5 and (slope or 0) > 0:
        label = "accumulation"
    elif ratio and ratio < 0.67 and (slope or 0) < 0:
        label = "distribution"
    return {"updown_ratio": ratio, "obv_slope": slope, "volume_zscore": z,
            "proxy_label": label,
            "rule": "proxy only: public volume data, not order-flow"}


def build_feature_row(rows: list[Row], vix_rows: list[Row] | None = None) -> dict:
    """Bundle every deterministic filter for one asset (the AI input row)."""
    return {
        "vwap": vwap_zscore(rows),
        "vix_velocity": vix_velocity(vix_rows),
        "volume_pressure": volume_pressure(rows),
    }
