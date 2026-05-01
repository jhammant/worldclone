"""Scoring metrics for sports forecasts.

Three lenses:
  - Pick accuracy (% correct binary calls)
  - Brier score on P(home wins) vs. resolved 0/1
  - Spread MAE (predicted margin vs. actual margin)
  - ROI vs. closing Vegas line (the only metric that matters for real money)
"""
from __future__ import annotations

from collections.abc import Iterable
from statistics import mean

from .brier import brier_one


def correct_pick(p_home_win: float, actual_winner: str) -> int:
    """1 if the bot's directional pick matches reality."""
    pick_home = p_home_win >= 0.5
    return 1 if (pick_home and actual_winner == "home") or (not pick_home and actual_winner == "away") else 0


def accuracy(p_home_winners: Iterable[float], actual_winners: Iterable[str]) -> float:
    p = list(p_home_winners)
    a = list(actual_winners)
    if not p:
        return float("nan")
    return mean(correct_pick(pi, ai) for pi, ai in zip(p, a, strict=True))


def brier(p_home_winners: Iterable[float], actual_winners: Iterable[str]) -> float:
    p = list(p_home_winners)
    a = list(actual_winners)
    if not p:
        return float("nan")
    outs = [1 if w == "home" else 0 for w in a]
    return mean(brier_one(pi, oi) for pi, oi in zip(p, outs, strict=True))


def spread_mae(predicted_margins: Iterable[float], actual_margins: Iterable[int]) -> float:
    pm = list(predicted_margins)
    am = list(actual_margins)
    if not pm:
        return float("nan")
    return mean(abs(p - a) for p, a in zip(pm, am, strict=True))


def moneyline_to_implied_prob(odds: int) -> float:
    """American odds → implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)


def vs_vegas_roi(
    p_home_winners: Iterable[float],
    actual_winners: Iterable[str],
    home_moneylines: Iterable[int | None],
    away_moneylines: Iterable[int | None],
    *,
    edge_threshold: float = 0.03,
    bet_size: float = 100.0,
) -> dict:
    """Compute ROI from betting whichever side has positive expected value vs. line.

    Skip games without a Vegas moneyline. Returns dict with bets_made, hit_rate,
    profit_dollars, roi_pct.
    """
    p_list = list(p_home_winners)
    a_list = list(actual_winners)
    h_list = list(home_moneylines)
    aw_list = list(away_moneylines)
    bets = 0
    profit = 0.0
    hits = 0
    for p, winner, h_ml, a_ml in zip(p_list, a_list, h_list, aw_list, strict=True):
        if h_ml is None or a_ml is None:
            continue
        ip_home = moneyline_to_implied_prob(h_ml)
        ip_away = moneyline_to_implied_prob(a_ml)
        # Bot's edge in each direction
        edge_home = p - ip_home
        edge_away = (1 - p) - ip_away
        side: str | None = None
        if edge_home >= edge_threshold and edge_home >= edge_away:
            side = "home"
        elif edge_away >= edge_threshold:
            side = "away"
        if side is None:
            continue
        bets += 1
        bet_won = (side == winner)
        ml = h_ml if side == "home" else a_ml
        if bet_won:
            hits += 1
            if ml > 0:
                profit += bet_size * ml / 100
            else:
                profit += bet_size * 100 / -ml
        else:
            profit -= bet_size
    return {
        "bets_made": bets,
        "hit_rate": hits / bets if bets else float("nan"),
        "profit_dollars": profit,
        "roi_pct": (profit / (bets * bet_size)) * 100 if bets else float("nan"),
    }
