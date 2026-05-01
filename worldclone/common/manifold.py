"""Manifold API helpers: load questions, fetch bet history."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from .io import ManifoldQuestion


def fetch_market(market_id: str) -> dict:
    """Fetch a single Manifold market by ID."""
    url = f"https://api.manifold.markets/v0/market/{urllib.parse.quote(market_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_bets(market_id: str, limit: int = 1000) -> list[dict]:
    """Fetch bet history for a market (used for time-averaged community probability)."""
    url = f"https://api.manifold.markets/v0/bets?contractId={urllib.parse.quote(market_id)}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def load_iran_cluster(path: str | Path = "data/iran_cluster.json") -> list[ManifoldQuestion]:
    """Load the curated Iran cluster questions."""
    with open(path) as f:
        raw = json.load(f)
    return [ManifoldQuestion(**q) for q in raw]


def time_averaged_prob(bets: list[dict], create_time_ms: int, close_time_ms: int) -> float:
    """Time-weighted average probability between create_time and close_time.

    bets is the list returned by /v0/bets (each has `createdTime`, `probAfter`).
    Earlier bets contribute proportionally to the time interval until the next bet.
    """
    if not bets:
        return 0.5
    # Sort by createdTime ascending
    sorted_bets = sorted(bets, key=lambda b: b.get("createdTime", 0))
    total_dt = 0
    weighted = 0.0
    prev_t = create_time_ms
    prev_p = 0.5  # neutral prior before first bet
    for b in sorted_bets:
        t = b.get("createdTime", prev_t)
        if t < prev_t:
            continue
        dt = t - prev_t
        weighted += prev_p * dt
        total_dt += dt
        prev_t = t
        prev_p = b.get("probAfter", prev_p)
    # Tail: from last bet to close
    if close_time_ms > prev_t:
        dt = close_time_ms - prev_t
        weighted += prev_p * dt
        total_dt += dt
    return weighted / total_dt if total_dt > 0 else prev_p
