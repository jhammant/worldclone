"""Fetch Manifold bet history for the Iran cluster + compute time-averaged community probabilities.

Output: data/iran_bet_history.json (one row per market, with raw bets and time-averaged prob).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from worldclone.common.manifold import fetch_bets, time_averaged_prob


def main() -> None:
    src = Path("data/iran_cluster.json")
    with src.open() as f:
        cluster = json.load(f)

    out = []
    for q in cluster:
        mid = q["id"]
        print(f"Fetching bets for {mid} ({q['question'][:60]}...)")
        bets = fetch_bets(mid, limit=2000)
        time_avg = time_averaged_prob(
            bets,
            create_time_ms=q["create_time_ms"],
            close_time_ms=q["close_time_ms"],
        )
        out.append({
            "id": mid,
            "question": q["question"],
            "n_bets": len(bets),
            "community_close": q.get("resolution_probability"),
            "community_time_avg": time_avg,
            # Don't dump full bets to keep file size manageable; keep timestamp + probAfter only
            "bet_trace": [
                {"t": b.get("createdTime"), "p": b.get("probAfter")}
                for b in sorted(bets, key=lambda x: x.get("createdTime", 0))
            ],
        })
        time.sleep(0.3)  # be polite

    dst = Path("data/iran_bet_history.json")
    with dst.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {len(out)} traces → {dst}")
    for row in out:
        print(f"  {row['id']}: close={row['community_close']:.3f} time_avg={row['community_time_avg']:.3f} ({row['n_bets']} bets)")


if __name__ == "__main__":
    main()
