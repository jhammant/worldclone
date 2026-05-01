"""Box office scoring metrics. Box office is log-normal so we report multiple lenses."""
from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import mean, median


def absolute_percentage_error(predicted: float, actual: float) -> float:
    """|pred - actual| / actual. Standard box office metric."""
    if actual <= 0:
        raise ValueError(f"actual must be positive, got {actual}")
    return abs(predicted - actual) / actual


def mape(predictions: Iterable[float], actuals: Iterable[float]) -> float:
    """Mean Absolute Percentage Error."""
    p = list(predictions)
    a = list(actuals)
    if len(p) != len(a):
        raise ValueError("length mismatch")
    if not p:
        return float("nan")
    return mean(absolute_percentage_error(pi, ai) for pi, ai in zip(p, a, strict=True))


def median_ape(predictions: Iterable[float], actuals: Iterable[float]) -> float:
    """Median APE — robust to one outrageous miss skewing the score."""
    p = list(predictions)
    a = list(actuals)
    if not p:
        return float("nan")
    return median(absolute_percentage_error(pi, ai) for pi, ai in zip(p, a, strict=True))


def log_absolute_error(predicted: float, actual: float) -> float:
    """|log10(pred) - log10(actual)|. Better than APE when predictions span orders of magnitude.

    log_ae=0.30 means off by 2x in either direction.
    log_ae=0.10 means off by ~26%.
    """
    if predicted <= 0 or actual <= 0:
        raise ValueError("both must be positive")
    return abs(math.log10(predicted) - math.log10(actual))


def log_mae(predictions: Iterable[float], actuals: Iterable[float]) -> float:
    p = list(predictions)
    a = list(actuals)
    if not p:
        return float("nan")
    return mean(log_absolute_error(pi, ai) for pi, ai in zip(p, a, strict=True))


def within_pct(predictions: Iterable[float], actuals: Iterable[float], pct: float) -> float:
    """Fraction of predictions within +/- pct (e.g. 0.20 for ±20%) of the actual."""
    p = list(predictions)
    a = list(actuals)
    if not p:
        return float("nan")
    hits = sum(1 for pi, ai in zip(p, a, strict=True) if absolute_percentage_error(pi, ai) <= pct)
    return hits / len(p)


def ci_coverage(
    ci_lows: Iterable[float],
    ci_highs: Iterable[float],
    actuals: Iterable[float],
) -> float:
    """Fraction of actuals that fell within their predicted [ci_low, ci_high].

    For a well-calibrated 80% CI, this should be ~0.80.
    """
    lows = list(ci_lows)
    highs = list(ci_highs)
    a = list(actuals)
    if not a:
        return float("nan")
    hits = sum(1 for lo, hi, ai in zip(lows, highs, a, strict=True) if lo <= ai <= hi)
    return hits / len(a)


def baseline_median_opening(actuals: Iterable[float]) -> float:
    """Trivial baseline: predict the median of past openings for every film."""
    a = list(actuals)
    if not a:
        return float("nan")
    return median(a)
