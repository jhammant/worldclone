"""Brier score utilities."""
from __future__ import annotations

import math
import random
from collections.abc import Iterable


def brier_one(p: float, outcome: int) -> float:
    """Single-question Brier score: (p - outcome)^2."""
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"probability out of range: {p}")
    if outcome not in (0, 1):
        raise ValueError(f"outcome must be 0 or 1, got {outcome}")
    return (p - outcome) ** 2


def brier_mean(probs: Iterable[float], outcomes: Iterable[int]) -> float:
    """Mean Brier across a set of (p, outcome) pairs."""
    p_list = list(probs)
    o_list = list(outcomes)
    if len(p_list) != len(o_list):
        raise ValueError("probs and outcomes must be same length")
    if not p_list:
        return float("nan")
    return sum(brier_one(p, o) for p, o in zip(p_list, o_list, strict=True)) / len(p_list)


def log_loss_one(p: float, outcome: int, eps: float = 1e-9) -> float:
    """Single-question log loss (for sanity check alongside Brier)."""
    p = min(max(p, eps), 1 - eps)
    return -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))


def log_loss_mean(probs: Iterable[float], outcomes: Iterable[int]) -> float:
    p_list = list(probs)
    o_list = list(outcomes)
    if not p_list:
        return float("nan")
    return sum(log_loss_one(p, o) for p, o in zip(p_list, o_list, strict=True)) / len(p_list)


def bootstrap_brier_ci(
    probs: list[float],
    outcomes: list[int],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap CI for the mean Brier by resampling questions with replacement.

    With N=7 questions this is mostly descriptive — flag in any writeup.
    """
    if len(probs) != len(outcomes):
        raise ValueError("length mismatch")
    rng = random.Random(seed)
    n = len(probs)
    if n == 0:
        return float("nan"), float("nan")
    samples = []
    for _ in range(n_bootstrap):
        idx = [rng.randrange(n) for _ in range(n)]
        b = sum(brier_one(probs[i], outcomes[i]) for i in idx) / n
        samples.append(b)
    samples.sort()
    alpha = (1 - confidence) / 2
    lo = samples[int(alpha * n_bootstrap)]
    hi = samples[int((1 - alpha) * n_bootstrap) - 1]
    return lo, hi


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for binomial proportion. Used for simulation
    probability estimates from N Monte Carlo runs."""
    if n == 0:
        return 0.0, 1.0
    # Two-sided z for given confidence
    z = {0.90: 1.6449, 0.95: 1.96, 0.99: 2.5758}.get(confidence, 1.96)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)
