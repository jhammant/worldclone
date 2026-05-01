"""Designed 1200x1200 social-media images for LinkedIn upload.

Three cards:
  1. weekend_card.png       — the four selections + treble/4-fold prices
  2. results_so_far.png     — Iran + box office + NBA headline numbers
  3. score_back_monday.png  — calendar teaser CTA ("results land Monday")

Style: dark navy background, accent yellow/green/red, big sans-serif type.
Designed for LinkedIn 1:1 in-feed where 1080–1200px square reads strongest.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

from worldclone.scoring.sports import moneyline_to_implied_prob
from worldclone.sports.uk_odds import american_to_fractional


# ---------------------------------------------------------- design tokens ---

BG = "#0E1525"           # deep navy
PANEL = "#1B2438"        # raised panel
PANEL_HI = "#2C3650"     # selected
TEXT = "#E8ECF4"
TEXT_DIM = "#9AA3B5"
ACCENT = "#F5C518"       # yellow (IMDB-y, attention)
GREEN = "#2EE07A"
RED = "#FF5C5C"
BLUE = "#5BA3FF"


def base_axes(figsize=(12, 12)):
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def rounded_panel(ax, x, y, w, h, color=PANEL, alpha=1.0, **kw):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.0,rounding_size=1.6",
        facecolor=color, edgecolor="none", alpha=alpha, **kw,
    )
    ax.add_patch(p)
    return p


# --------------------------------------------------------- weekend card ----

def _short_context(g: dict) -> str:
    """Compact one-line context fit for a card row.

    Prefers a "Game N · Series X-Y" form for playoff games; falls back to a
    truncated first sentence from `series_context` for league fixtures.
    """
    sc = g.get("series_context", "") or ""
    if g.get("is_playoff"):
        # "Eastern Conference 1st Round, Game 6. ..."
        first = sc.split(".")[0]
        return first[:40]
    # League / cup — keep it really short
    return "Premier League matchday"


def load_picks() -> list[dict]:
    games = {g["id"]: g for g in json.load(
        Path("data/sports/weekend_2026_05_01.json").open())["games"]}
    rows = []
    with Path("results/sports_forecasts/weekend_2026_05_01/forecasts.jsonl"
              ).open() as f:
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
                    "team": g["home_team"],
                    "vs": g["away_team"],
                    "sport": g["sport"].upper(),
                    "context": _short_context(g),
                    "model_pct": bot_h * 100,
                    "bookie_pct": ip_h * 100,
                    "edge_pp": edge_h * 100,
                    "frac": american_to_fractional(h_ml),
                })
            else:
                rows.append({
                    "team": g["away_team"],
                    "vs": g["home_team"],
                    "sport": g["sport"].upper(),
                    "context": _short_context(g),
                    "model_pct": bot_a * 100,
                    "bookie_pct": ip_a * 100,
                    "edge_pp": edge_a * 100,
                    "frac": american_to_fractional(a_ml),
                })
    return [r for r in sorted(rows, key=lambda r: -r["edge_pp"])
            if r["edge_pp"] >= 2.0]


def card_weekend(picks: list[dict]) -> None:
    fig, ax = base_axes()
    # Header
    ax.text(50, 95, "WEEKEND CARD", color=TEXT, fontsize=42,
            fontweight="bold", ha="center", va="center", family="sans-serif")
    ax.text(50, 90.5, "1–3 May 2026  ·  4 selections  ·  publicly logged",
            color=TEXT_DIM, fontsize=16, ha="center", va="center")
    ax.plot([15, 85], [87.5, 87.5], color="#3A4561", linewidth=1)

    # Selection cards
    y0 = 80
    h = 12.5
    gap = 1.5
    for i, p in enumerate(picks):
        y = y0 - i * (h + gap)
        rounded_panel(ax, 8, y - h, 84, h, color=PANEL)
        # Sport badge
        rounded_panel(ax, 10, y - 3.5, 7, 2.5, color=PANEL_HI)
        ax.text(13.5, y - 2.25, p["sport"], color=ACCENT, fontsize=11,
                fontweight="bold", ha="center", va="center")
        # Team name + matchup
        ax.text(19, y - 3, p["team"], color=TEXT, fontsize=20,
                fontweight="bold", va="center")
        ax.text(19, y - 6.2, f"vs {p['vs']}  ·  {p['context']}",
                color=TEXT_DIM, fontsize=12, va="center")
        # Edge pill bottom-left
        edge_color = GREEN
        ax.text(19, y - 9.2, f"model {p['model_pct']:.1f}%  vs  bookie {p['bookie_pct']:.1f}%",
                color=TEXT_DIM, fontsize=11, va="center")
        rounded_panel(ax, 19, y - 11.5, 11, 2.0,
                      color="#1F3A2A")
        ax.text(24.5, y - 10.5, f"+{p['edge_pp']:.1f}pp edge",
                color=edge_color, fontsize=11, fontweight="bold",
                ha="center", va="center")
        # Big price right
        ax.text(85, y - 5.5, p["frac"], color=ACCENT, fontsize=44,
                fontweight="bold", ha="right", va="center")
        ax.text(85, y - 9.5, "best UK high-street",
                color=TEXT_DIM, fontsize=10, ha="right", va="center")

    # Treble + 4-fold strip
    y_acc = 22
    rounded_panel(ax, 8, y_acc - 8, 84, 8, color=PANEL_HI)
    ax.text(28, y_acc - 2.4, "TREBLE", color=TEXT_DIM, fontsize=12,
            fontweight="bold", ha="center", va="center")
    ax.text(28, y_acc - 5.0, "≈ 7/1", color=ACCENT, fontsize=26,
            fontweight="bold", ha="center", va="center")
    ax.text(28, y_acc - 7.0, "+20.9% theoretical EV", color=GREEN,
            fontsize=11, ha="center", va="center")
    ax.plot([50, 50], [y_acc - 7.5, y_acc - 0.5], color="#3A4561",
            linewidth=1)
    ax.text(72, y_acc - 2.4, "4-FOLD", color=TEXT_DIM, fontsize=12,
            fontweight="bold", ha="center", va="center")
    ax.text(72, y_acc - 5.0, "≈ 15/1", color=ACCENT, fontsize=26,
            fontweight="bold", ha="center", va="center")
    ax.text(72, y_acc - 7.0, "+23.9% theoretical EV", color=GREEN,
            fontsize=11, ha="center", va="center")

    # Footer CTA
    ax.text(50, 9.5, "score-back Monday 4 May  ·  win or lose",
            color=TEXT, fontsize=14, fontweight="bold", ha="center",
            va="center")
    ax.text(50, 6.0, "follow → results next week",
            color=BLUE, fontsize=11, ha="center", va="center")
    ax.text(50, 2.5, "github.com/jhammant/worldclone",
            color=TEXT_DIM, fontsize=10, ha="center", va="center",
            family="monospace")

    out = Path("docs/images/social_weekend_card.png")
    plt.tight_layout(pad=0)
    plt.savefig(out, facecolor=BG, dpi=100, bbox_inches="tight",
                pad_inches=0.3)
    print(f"wrote {out} ({out.stat().st_size//1024} KB)")
    plt.close()


# ------------------------------------------------------ results_so_far -----

def card_results_so_far() -> None:
    fig, ax = base_axes()
    ax.text(50, 94, "RESULTS SO FAR", color=TEXT, fontsize=42,
            fontweight="bold", ha="center", va="center")
    ax.text(50, 89.5, "every number reproducible from the repo",
            color=TEXT_DIM, fontsize=15, ha="center", va="center")
    ax.plot([15, 85], [86.5, 86.5], color="#3A4561", linewidth=1)

    # Three blocks: Iran | Box office | NBA
    y0 = 78
    block_h = 22
    block_gap = 2.5

    # --- 1. Iran cluster
    y = y0
    rounded_panel(ax, 8, y - block_h, 84, block_h, color=PANEL)
    ax.text(11, y - 4, "GEOPOLITICS", color=ACCENT, fontsize=12,
            fontweight="bold", va="center")
    ax.text(11, y - 8.5, "Iran 2026 cluster, 6 questions, post-resolution",
            color=TEXT, fontsize=14, va="center")
    # 3 brier numbers
    ax.text(20, y - 14.5, "0.001", color=GREEN, fontsize=32,
            fontweight="bold", ha="center", va="center")
    ax.text(20, y - 19, "Manifold crowd", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(50, y - 14.5, "0.131", color=BLUE, fontsize=32,
            fontweight="bold", ha="center", va="center")
    ax.text(50, y - 19, "multi-agent sim", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(80, y - 14.5, "0.272", color=RED, fontsize=32,
            fontweight="bold", ha="center", va="center")
    ax.text(80, y - 19, "LLM forecaster", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(50, y - 21.7, "Brier score (lower is better)  ·  naive 50% = 0.250",
            color=TEXT_DIM, fontsize=10, ha="center", va="center",
            style="italic")

    # --- 2. Box office
    y = y0 - block_h - block_gap
    rounded_panel(ax, 8, y - block_h, 84, block_h, color=PANEL)
    ax.text(11, y - 4, "BOX OFFICE", color=ACCENT, fontsize=12,
            fontweight="bold", va="center")
    ax.text(11, y - 8.5, "10 wide releases, opening-weekend forecast",
            color=TEXT, fontsize=14, va="center")
    ax.text(20, y - 14.5, "15.9%", color=GREEN, fontsize=30,
            fontweight="bold", ha="center", va="center")
    ax.text(20, y - 19, "MAPE (model)", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(50, y - 14.5, "80%", color=BLUE, fontsize=30,
            fontweight="bold", ha="center", va="center")
    ax.text(50, y - 19, "80% CI coverage", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(80, y - 14.5, "101%", color=RED, fontsize=30,
            fontweight="bold", ha="center", va="center")
    ax.text(80, y - 19, "MAPE (naive)", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(50, y - 21.7,
            "8 of 10 inside the 80% interval — calibrated, not lucky",
            color=TEXT_DIM, fontsize=10, ha="center", va="center",
            style="italic")

    # --- 3. NBA picks
    y = y0 - 2 * (block_h + block_gap)
    rounded_panel(ax, 8, y - block_h, 84, block_h, color=PANEL)
    ax.text(11, y - 4, "NBA PICKS LIVE", color=ACCENT, fontsize=12,
            fontweight="bold", va="center")
    ax.text(11, y - 8.5, "playoff games scored against the actual result",
            color=TEXT, fontsize=14, va="center")
    ax.text(35, y - 14.5, "4 / 7", color=GREEN, fontsize=42,
            fontweight="bold", ha="center", va="center")
    ax.text(35, y - 19, "directional hit rate", color=TEXT_DIM, fontsize=11,
            ha="center", va="center")
    ax.text(70, y - 14.5, "57%", color=BLUE, fontsize=36,
            fontweight="bold", ha="center", va="center")
    ax.text(70, y - 19, "Wilson 95% CI [25%, 80%]", color=TEXT_DIM,
            fontsize=10, ha="center", va="center")

    # Footer
    ax.text(50, 4, "github.com/jhammant/worldclone",
            color=TEXT_DIM, fontsize=10, ha="center", va="center",
            family="monospace")

    out = Path("docs/images/social_results_so_far.png")
    plt.tight_layout(pad=0)
    plt.savefig(out, facecolor=BG, dpi=100, bbox_inches="tight",
                pad_inches=0.3)
    print(f"wrote {out} ({out.stat().st_size//1024} KB)")
    plt.close()


# ------------------------------------------------- score-back Monday teaser -

def card_score_back() -> None:
    fig, ax = base_axes()
    ax.text(50, 92, "SCORE-BACK MONDAY", color=TEXT, fontsize=40,
            fontweight="bold", ha="center", va="center")
    ax.text(50, 87.5, "win or lose, the original picks are hash-chained",
            color=TEXT_DIM, fontsize=14, ha="center", va="center")
    ax.plot([15, 85], [84, 84], color="#3A4561", linewidth=1)

    # 4-day timeline (Fri 1 → Mon 4)
    days = [("FRI", "1", "picks logged"),
            ("SAT", "2", "EPL + Guineas"),
            ("SUN", "3", "Man Utd v LIV"),
            ("MON", "4", "score-back post")]
    y_t = 65
    panel_w = 18
    panel_h = 22
    gap = 4
    total_w = 4 * panel_w + 3 * gap
    x_start = (100 - total_w) / 2
    for i, (lbl, num, sub) in enumerate(days):
        x = x_start + i * (panel_w + gap)
        is_today = (i == 0)
        is_target = (i == 3)
        if is_today:
            color = "#1F3A2A"
            border = GREEN
        elif is_target:
            color = "#3A2A1F"
            border = ACCENT
        else:
            color = PANEL
            border = None
        rounded_panel(ax, x, y_t - panel_h, panel_w, panel_h, color=color)
        if border is not None:
            rect = mpatches.FancyBboxPatch(
                (x, y_t - panel_h), panel_w, panel_h,
                boxstyle="round,pad=0.0,rounding_size=1.6",
                facecolor="none", edgecolor=border, linewidth=2.5)
            ax.add_patch(rect)
        ax.text(x + panel_w / 2, y_t - 4, lbl, color=TEXT_DIM, fontsize=14,
                fontweight="bold", ha="center", va="center")
        big_color = ACCENT if is_target else (GREEN if is_today else TEXT)
        ax.text(x + panel_w / 2, y_t - 11, num, color=big_color,
                fontsize=46, fontweight="bold", ha="center", va="center")
        ax.text(x + panel_w / 2, y_t - 18, sub, color=TEXT_DIM,
                fontsize=10, ha="center", va="center")

    # The bets summary panel
    y_b = 35
    rounded_panel(ax, 8, y_b - 18, 84, 18, color=PANEL)
    ax.text(50, y_b - 3, "the four picks", color=TEXT_DIM, fontsize=12,
            fontweight="bold", ha="center", va="center")
    picks_short = [
        ("Canadiens G6", "10/11"),
        ("Golden Knights G6", "5/6"),
        ("Man Utd v Liverpool", "13/10"),
        ("Bruins G6", "10/11"),
    ]
    for i, (name, frac) in enumerate(picks_short):
        x = 14 + (i % 2) * 42
        y = y_b - 8 - (i // 2) * 6
        ax.text(x, y, "▸", color=ACCENT, fontsize=14, va="center")
        ax.text(x + 2, y, name, color=TEXT, fontsize=13, va="center")
        ax.text(x + 38, y, frac, color=ACCENT, fontsize=14,
                fontweight="bold", ha="right", va="center")

    # CTA
    ax.text(50, 11, "follow for the result", color=BLUE, fontsize=18,
            fontweight="bold", ha="center", va="center")
    ax.text(50, 6, "github.com/jhammant/worldclone",
            color=TEXT_DIM, fontsize=10, ha="center", va="center",
            family="monospace")

    out = Path("docs/images/social_score_back_monday.png")
    plt.tight_layout(pad=0)
    plt.savefig(out, facecolor=BG, dpi=100, bbox_inches="tight",
                pad_inches=0.3)
    print(f"wrote {out} ({out.stat().st_size//1024} KB)")
    plt.close()


# --------------------------------------------------------------------- run -

if __name__ == "__main__":
    Path("docs/images").mkdir(parents=True, exist_ok=True)
    picks = load_picks()
    print(f"loaded {len(picks)} qualifying picks")
    card_weekend(picks)
    card_results_so_far()
    card_score_back()
