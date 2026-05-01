"""Weekend picks scoreboard — bot prob vs Vegas no-vig prob, edge in pp.

Reads the canonical weekend forecast + games and produces
docs/images/weekend_picks.png.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from worldclone.scoring.sports import moneyline_to_implied_prob


FORECASTS = Path("results/sports_forecasts/weekend_2026_05_01/forecasts.jsonl")
GAMES = Path("data/sports/weekend_2026_05_01.json")
OUT = Path("docs/images/weekend_picks.png")


def load_picks() -> list[dict]:
    games = {g["id"]: g for g in json.load(GAMES.open())["games"]}
    rows = []
    with FORECASTS.open() as f:
        for line in f:
            d = json.loads(line)
            g = games.get(d["game_id"])
            if not g:
                continue
            h_ml = g.get("vegas_home_moneyline")
            a_ml = g.get("vegas_away_moneyline")
            d_ml = g.get("vegas_draw_moneyline")
            if h_ml is None or a_ml is None:
                continue
            ip_h = moneyline_to_implied_prob(h_ml)
            ip_a = moneyline_to_implied_prob(a_ml)
            if d_ml is not None:
                ip_d = moneyline_to_implied_prob(d_ml)
                tot = ip_h + ip_a + ip_d
                ip_h, ip_a = ip_h / tot, ip_a / tot
                split_a = ip_a / (ip_a + ip_d / tot)
                bot_h = d["p_home_win"]
                bot_a = (1 - bot_h) * split_a
            else:
                tot = ip_h + ip_a
                ip_h, ip_a = ip_h / tot, ip_a / tot
                bot_h = d["p_home_win"]
                bot_a = 1 - bot_h
            edge_h = bot_h - ip_h
            edge_a = bot_a - ip_a
            if edge_h >= edge_a:
                rows.append({
                    "label": f"{g['home_team_short']} home v {g['away_team_short']}",
                    "matchup": f"{g['home_team']} vs {g['away_team']}",
                    "sport": g["sport"].upper(),
                    "bot": bot_h, "vegas": ip_h, "edge_pp": edge_h * 100,
                })
            else:
                rows.append({
                    "label": f"{g['away_team_short']} away at {g['home_team_short']}",
                    "matchup": f"{g['away_team']} at {g['home_team']}",
                    "sport": g["sport"].upper(),
                    "bot": bot_a, "vegas": ip_a, "edge_pp": edge_a * 100,
                })
    rows = [r for r in rows if r["edge_pp"] >= 2.0]
    rows.sort(key=lambda r: r["edge_pp"], reverse=True)
    return rows


def plot(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(10, max(4, 0.9 * len(rows) + 2)), dpi=150)
    n = len(rows)
    y_positions = list(range(n))[::-1]
    bar_height = 0.35
    bot_color = "#1f77b4"
    vegas_color = "#bbbbbb"
    for y, r in zip(y_positions, rows):
        ax.barh(y + bar_height / 2, r["bot"] * 100, bar_height,
                color=bot_color, edgecolor="black", linewidth=0.5)
        ax.barh(y - bar_height / 2, r["vegas"] * 100, bar_height,
                color=vegas_color, edgecolor="black", linewidth=0.5)
        ax.text(r["bot"] * 100 + 0.6, y + bar_height / 2,
                f"{r['bot']*100:.1f}%", va="center", fontsize=9)
        ax.text(r["vegas"] * 100 + 0.6, y - bar_height / 2,
                f"{r['vegas']*100:.1f}%", va="center", fontsize=9, color="#666")
        ax.text(70, y, f"+{r['edge_pp']:.1f}pp",
                va="center", fontsize=10, fontweight="bold",
                color="#2ca02c", bbox=dict(boxstyle="round,pad=0.3",
                facecolor="#eaf6ea", edgecolor="#2ca02c", linewidth=0.8))
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"{r['sport']}  {r['matchup']}" for r in rows],
                       fontsize=9)
    ax.set_xlim(0, 80)
    ax.set_xlabel("Probability of pick winning (%)")
    ax.set_title("Weekend May 1–3, 2026 — picks publicly logged before tip-off\n"
                 "3-leg parlay +20.9% EV  ·  4-leg +23.9% EV  ·  scored Monday",
                 fontsize=12)
    legend_elems = [
        Patch(facecolor=bot_color, edgecolor="black", label="Bot probability"),
        Patch(facecolor=vegas_color, edgecolor="black",
              label="Vegas no-vig implied"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", framealpha=0.95)
    ax.grid(True, axis="x", alpha=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    plot(load_picks())
