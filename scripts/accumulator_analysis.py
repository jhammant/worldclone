"""Accumulator analyzer.

Reads sports forecasts (P_home_win + Vegas moneylines) and produces:
  - Per-event table with edge, decimal odds, single-bet EV
  - Suggested 3/4/5-leg accumulators
  - Vegas implied joint P vs. bot's joint P (independence assumption)
  - Honest caveats

This is a *forward* analysis tool. Run after the forecaster completes; the
output is what to bet (or just record) before the games start.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

from worldclone.scoring.sports import moneyline_to_implied_prob


def american_to_decimal(odds: int) -> float:
    """American odds → decimal odds (e.g. -150 → 1.667, +130 → 2.30)."""
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / -odds


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--forecasts", required=True, help="Path to forecasts.jsonl")
    p.add_argument("--games", required=True, help="Path to games.json (the same one passed to the forecaster)")
    p.add_argument("--bankroll", type=float, default=100.0, help="Notional bankroll for stake-sizing examples")
    p.add_argument("--kelly-fraction", type=float, default=0.25, help="Fraction of full Kelly to wager (typical sharp: 0.1-0.5)")
    p.add_argument("--min-edge-pp", type=float, default=2.0, help="Minimum edge (percentage points) to include a leg in the accumulator")
    p.add_argument("--out-md", default=None, help="Optional markdown output file")
    return p.parse_args()


def kelly_fraction(p: float, decimal_odds: float) -> float:
    """Full-Kelly stake fraction.
    f* = (bp - q) / b, where b = decimal_odds - 1, p = bot's win prob, q = 1-p.
    Returns 0 if no edge.
    """
    b = decimal_odds - 1
    if b <= 0:
        return 0.0
    f = (b * p - (1 - p)) / b
    return max(0.0, f)


def load_forecasts_and_games(forecasts_path: Path, games_path: Path) -> list[dict]:
    """Returns one row per game with both bot and Vegas info."""
    games = {g["id"]: g for g in json.load(games_path.open())["games"]}
    forecasts = {}
    with forecasts_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                forecasts[d["game_id"]] = d
    rows = []
    for gid, fc in forecasts.items():
        g = games.get(gid)
        if g is None:
            continue
        h_ml = g.get("vegas_home_moneyline")
        a_ml = g.get("vegas_away_moneyline")
        d_ml = g.get("vegas_draw_moneyline")
        if h_ml is None or a_ml is None:
            continue

        bot_p_home = fc["p_home_win"]
        if d_ml is not None:
            # 3-way market (soccer). Bot only outputs P(home win); split the
            # remaining probability between away/draw using Vegas as a prior.
            ip_home_raw = moneyline_to_implied_prob(h_ml)
            ip_away_raw = moneyline_to_implied_prob(a_ml)
            ip_draw_raw = moneyline_to_implied_prob(d_ml)
            total = ip_home_raw + ip_away_raw + ip_draw_raw
            ip_home = ip_home_raw / total
            ip_away = ip_away_raw / total
            ip_draw = ip_draw_raw / total
            split_away = ip_away / (ip_away + ip_draw)
            bot_p_away = (1 - bot_p_home) * split_away
            edge_home = bot_p_home - ip_home
            edge_away = bot_p_away - ip_away
        else:
            # Binary market — normalise home/away no-vig as before.
            ip_home_raw = moneyline_to_implied_prob(h_ml)
            ip_away_raw = moneyline_to_implied_prob(a_ml)
            total = ip_home_raw + ip_away_raw
            ip_home = ip_home_raw / total
            ip_away = ip_away_raw / total
            edge_home = bot_p_home - ip_home
            edge_away = (1 - bot_p_home) - ip_away

        # Pick whichever side has positive edge
        if edge_home >= edge_away:
            side = "home"
            team = g["home_team"]
            ml = h_ml
            edge = edge_home
            bot_p = bot_p_home
            vegas_p = ip_home
        else:
            side = "away"
            team = g["away_team"]
            ml = a_ml
            edge = edge_away
            bot_p = bot_p_away if d_ml is not None else (1 - bot_p_home)
            vegas_p = ip_away

        decimal = american_to_decimal(ml)
        ev_per_dollar = bot_p * decimal - 1
        kelly_f = kelly_fraction(bot_p, decimal)

        rows.append({
            "game_id": gid,
            "matchup": f"{g['away_team']} @ {g['home_team']}",
            "sport": g["sport"],
            "tip_off": g.get("game_date"),
            "context": g.get("series_context", "")[:80],
            "side": side,
            "team": team,
            "moneyline": ml,
            "decimal_odds": decimal,
            "vegas_implied_p": vegas_p,
            "bot_p_home": bot_p_home,
            "bot_p_pick": bot_p,
            "edge_pp": edge * 100,
            "ev_per_dollar": ev_per_dollar,
            "kelly_full": kelly_f,
            "predicted_margin_home": fc.get("predicted_margin_home"),
            "ensemble_p_home": fc.get("ensemble_p_home", []),
        })
    rows.sort(key=lambda r: r["edge_pp"], reverse=True)
    return rows


def render_per_event_table(rows: list[dict], bankroll: float, kelly_frac: float) -> str:
    out = ["## Per-event analysis", ""]
    out.append("| Event | Pick | Bot P | Vegas P (no-vig) | Edge | ML | Decimal | EV/$1 | Quarter-Kelly stake |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        stake = bankroll * r["kelly_full"] * kelly_frac
        out.append(
            f"| {r['matchup']} ({r['sport']}) | {r['team']} ({r['side']}) | "
            f"{r['bot_p_pick']*100:.1f}% | {r['vegas_implied_p']*100:.1f}% | "
            f"{r['edge_pp']:+.1f}pp | {r['moneyline']:+d} | {r['decimal_odds']:.2f} | "
            f"{r['ev_per_dollar']*100:+.1f}% | ${stake:.2f} |"
        )
    return "\n".join(out)


def render_accumulator(rows: list[dict], min_edge_pp: float, n_legs: int, bankroll: float, kelly_frac: float) -> str:
    """Pick the top n_legs legs by edge, all with edge > min_edge_pp, and price the parlay."""
    qualifying = [r for r in rows if r["edge_pp"] >= min_edge_pp]
    if len(qualifying) < n_legs:
        return f"\n### {n_legs}-leg accumulator: not enough legs with edge ≥ {min_edge_pp}pp ({len(qualifying)} qualifying)\n"

    legs = qualifying[:n_legs]
    combined_decimal = 1.0
    bot_joint_p = 1.0
    vegas_joint_p = 1.0
    for r in legs:
        combined_decimal *= r["decimal_odds"]
        bot_joint_p *= r["bot_p_pick"]
        vegas_joint_p *= r["vegas_implied_p"]

    ev_per_dollar = bot_joint_p * combined_decimal - 1
    # Kelly for parlay: same formula, p = bot_joint, b = combined_decimal - 1
    kelly_f = kelly_fraction(bot_joint_p, combined_decimal)
    stake = bankroll * kelly_f * kelly_frac

    lines = []
    lines.append(f"\n### {n_legs}-leg accumulator (top {n_legs} legs by edge)\n")
    lines.append("Legs:")
    for i, r in enumerate(legs, 1):
        lines.append(
            f"  {i}. {r['team']} ({r['matchup']}) — bot {r['bot_p_pick']*100:.1f}% vs Vegas {r['vegas_implied_p']*100:.1f}%  edge {r['edge_pp']:+.1f}pp"
        )
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Combined decimal odds | {combined_decimal:.2f}x |")
    lines.append(f"| Bot joint P (independence assumption) | {bot_joint_p*100:.2f}% |")
    lines.append(f"| Vegas joint implied P (no-vig, independence) | {vegas_joint_p*100:.2f}% |")
    lines.append(f"| EV per $1 stake | {ev_per_dollar*100:+.1f}% |")
    lines.append(f"| Quarter-Kelly stake (out of ${bankroll:.0f} bankroll) | ${stake:.2f} |")
    lines.append("")
    if ev_per_dollar > 0:
        payoff = stake * combined_decimal
        lines.append(f"**If all {n_legs} legs hit**: stake ${stake:.2f} returns ${payoff:.2f} (profit ${payoff-stake:+.2f})")
    else:
        lines.append(f"⚠️ Negative EV — bot's joint probability is below break-even. Skip this accumulator.")
    return "\n".join(lines)


def render_singles_alternative(rows: list[dict], min_edge_pp: float, bankroll: float, kelly_frac: float) -> str:
    qualifying = [r for r in rows if r["edge_pp"] >= min_edge_pp]
    if not qualifying:
        return "\n### Single-bet alternative: no legs meet edge threshold\n"
    out = ["\n### Single-bet alternative (every qualifying leg as a straight bet)", ""]
    out.append("| Pick | Stake (¼ Kelly) | If wins, returns | EV/$ | EV ($) |")
    out.append("|---|---|---|---|---|")
    total_ev_dollars = 0.0
    total_stake = 0.0
    for r in qualifying:
        stake = bankroll * r["kelly_full"] * kelly_frac
        return_if_win = stake * r["decimal_odds"]
        ev_dollars = stake * r["ev_per_dollar"]
        total_stake += stake
        total_ev_dollars += ev_dollars
        out.append(
            f"| {r['team']} ({r['matchup']}) | ${stake:.2f} | ${return_if_win:.2f} | "
            f"{r['ev_per_dollar']*100:+.1f}% | ${ev_dollars:+.2f} |"
        )
    out.append("")
    out.append(f"**Total**: ${total_stake:.2f} staked across {len(qualifying)} legs → expected profit ${total_ev_dollars:+.2f}")
    return "\n".join(out)


def main() -> int:
    args = parse_args()
    forecasts = Path(args.forecasts)
    games = Path(args.games)
    rows = load_forecasts_and_games(forecasts, games)
    if not rows:
        print("No scoreable forecasts found.", file=sys.stderr)
        return 1

    sections = []
    sections.append(f"# Tonight's lineup — accumulator analysis\n")
    sections.append(f"Bankroll: ${args.bankroll:.0f}  |  Kelly fraction: {args.kelly_fraction:.2f}  |  Min edge for accumulator: {args.min_edge_pp:.1f}pp\n")
    sections.append(render_per_event_table(rows, args.bankroll, args.kelly_fraction))

    sections.append("\n## Accumulator candidates")
    for n in (3, 4, 5):
        if len(rows) >= n:
            sections.append(render_accumulator(rows, args.min_edge_pp, n, args.bankroll, args.kelly_fraction))

    sections.append(render_singles_alternative(rows, args.min_edge_pp, args.bankroll, args.kelly_fraction))

    sections.append("""
## Honest caveats

- **Independence assumption is wrong.** Real-world legs correlate (shared news cycle, weather, broadcast slot). Joint P from multiplying singles is an upper bound; correlated risks → fewer "all hit" outcomes than the math suggests.
- **Sample size is N=5.** A favorable EV here is no proof of edge; could easily be variance.
- **Sportsbook accumulator vig compounds.** A real sportsbook would price these worse than the implied joint odds shown.
- **Quarter-Kelly is conservative.** Going full Kelly on parlays is ill-advised when edge confidence is low.
- **Use this as an immutable record + thinking exercise**, not a betting strategy without independent validation.
""")

    text = "\n".join(sections)
    if args.out_md:
        Path(args.out_md).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
