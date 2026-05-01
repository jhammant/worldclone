"""Score sports game forecasts against actual outcomes + Vegas lines."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worldclone.scoring.sports import accuracy, brier, spread_mae, vs_vegas_roi
from worldclone.sports.schemas import Game, GameForecast


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--games", default="data/sports/games.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Run dir missing: {run_dir}", file=sys.stderr)
        return 1

    with Path(args.games).open() as f:
        raw = json.load(f)
    games = {g["id"]: Game(**g) for g in raw["games"]}

    forecasts: dict[str, GameForecast] = {}
    f = run_dir / "forecasts.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                forecasts[d["game_id"]] = GameForecast(**d)

    rows = []
    for gid, fc in forecasts.items():
        g = games.get(gid)
        if g is None or g.actual_winner is None:
            rows.append({"id": gid, "p_home": fc.p_home_win, "margin": fc.predicted_margin_home, "actual": None})
            continue
        rows.append({
            "id": gid,
            "matchup": f"{g.away_team} @ {g.home_team}",
            "date": g.game_date,
            "p_home": fc.p_home_win,
            "predicted_margin": fc.predicted_margin_home,
            "actual_winner": g.actual_winner,
            "actual_margin": g.actual_margin_home,
            "vegas_home_ml": g.vegas_home_moneyline,
            "vegas_away_ml": g.vegas_away_moneyline,
        })

    scored = [r for r in rows if r.get("actual_winner") is not None]
    if not scored:
        print("No games have ground truth populated.")
        return 0

    p_list = [r["p_home"] for r in scored]
    a_list = [r["actual_winner"] for r in scored]
    m_pred = [r["predicted_margin"] for r in scored]
    m_act = [r["actual_margin"] for r in scored]
    h_ml = [r["vegas_home_ml"] for r in scored]
    a_ml = [r["vegas_away_ml"] for r in scored]

    acc = accuracy(p_list, a_list)
    br = brier(p_list, a_list)
    smae = spread_mae(m_pred, m_act)
    roi = vs_vegas_roi(p_list, a_list, h_ml, a_ml)

    lines = ["# Sports forecaster — Report", ""]
    lines.append(f"Run: `{run_dir}`")
    lines.append(f"Games scored: {len(scored)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Pick accuracy | {acc*100:.1f}% |")
    lines.append(f"| Brier (lower better) | {br:.4f} |")
    lines.append(f"| Spread MAE (points) | {smae:.2f} |")
    lines.append(f"| Vegas-edge bets made | {roi['bets_made']} |")
    if roi['bets_made']:
        lines.append(f"| Bet hit rate | {roi['hit_rate']*100:.1f}% |")
        lines.append(f"| Profit at $100/bet | ${roi['profit_dollars']:+.0f} |")
        lines.append(f"| ROI vs Vegas | {roi['roi_pct']:+.1f}% |")
    lines.append("")
    lines.append("## Per-game")
    lines.append("")
    lines.append("| Date | Matchup | P(home) | Pred margin | Actual | Hit? |")
    lines.append("|---|---|---|---|---|---|")
    for r in scored:
        winner = r["actual_winner"]
        pick_home = r["p_home"] >= 0.5
        hit = (pick_home and winner == "home") or (not pick_home and winner == "away")
        lines.append(
            f"| {r['date']} | {r['matchup']} | {r['p_home']:.2f} | "
            f"{r['predicted_margin']:+.1f} | {r['actual_margin']:+d} ({winner}) | "
            f"{'✓' if hit else '✗'} |"
        )
    report = "\n".join(lines)
    (run_dir / "report.md").write_text(report)
    (run_dir / "scores.json").write_text(json.dumps({
        "accuracy": acc, "brier": br, "spread_mae": smae, "roi": roi, "rows": rows,
    }, indent=2, default=str))
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
