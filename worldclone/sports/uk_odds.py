"""UK-style odds conversion + display utilities.

UK punters and bookmakers use **fractional** odds ("13/10", "evens", "4/6")
not American moneyline. This helper converts a decimal price to the nearest
standard fractional bet on a UK board, plus formatting helpers.

Standard UK ladder used by Ladbrokes / Sky Bet / Bet365 / Coral / Paddy Power.
"""
from __future__ import annotations

from fractions import Fraction


# Industry-standard fractional ladder. Pulled from the price-board common
# to UK books; covers the realistic punting range (1/5 thru 50/1).
_LADDER_FRAC = [
    "1/5", "2/9", "1/4", "2/7", "3/10", "1/3", "4/11", "2/5", "4/9",
    "9/20", "1/2", "8/15", "4/7", "8/13", "4/6", "8/11", "4/5", "5/6",
    "10/11", "1/1", "11/10", "6/5", "5/4", "13/10", "11/8", "7/5", "6/4",
    "8/5", "13/8", "7/4",
    "15/8", "2/1", "9/4", "5/2", "11/4", "3/1", "10/3", "7/2", "4/1",
    "9/2", "5/1", "11/2", "6/1", "13/2", "7/1", "15/2", "8/1", "9/1",
    "10/1", "11/1", "12/1", "14/1", "16/1", "18/1", "20/1", "25/1",
    "33/1", "40/1", "50/1",
]


def fractional_to_decimal(frac_str: str) -> float:
    """'13/10' -> 2.30, 'evens' / '1/1' -> 2.0."""
    s = frac_str.strip().lower()
    if s in {"evens", "evs", "even", "1/1"}:
        return 2.0
    f = Fraction(s)
    return 1.0 + float(f)


def decimal_to_fractional(decimal: float) -> str:
    """Round a decimal price to the nearest standard UK fractional rung.

    `1.95 -> '10/11'`, `2.30 -> '13/10'`, `2.0 -> 'evens'`.
    """
    if decimal <= 1.0:
        return "1/100"  # absurd but safe
    target = decimal - 1.0
    best = None
    best_diff = float("inf")
    for f in _LADDER_FRAC:
        rung = float(Fraction(f))
        diff = abs(rung - target)
        if diff < best_diff:
            best_diff = diff
            best = f
    if best == "1/1":
        return "evens"
    return best


def american_to_fractional(american: int) -> str:
    """`-110 -> '10/11'`, `+130 -> '13/10'`."""
    if american > 0:
        decimal = 1.0 + american / 100.0
    else:
        decimal = 1.0 + 100.0 / -american
    return decimal_to_fractional(decimal)


def format_pair(decimal: float) -> str:
    """`1.95 -> '10/11 (1.95)'` — for inline display."""
    return f"{decimal_to_fractional(decimal)} ({decimal:.2f})"


def implied_prob_from_fractional(frac_str: str) -> float:
    """`'13/10'` (decimal 2.30) -> 0.4348."""
    return 1.0 / fractional_to_decimal(frac_str)
