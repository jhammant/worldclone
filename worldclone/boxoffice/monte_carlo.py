"""Monte Carlo simulator for first-week box office.

Given an opening-weekend forecast (point + 80% CI), sample N possible trajectories:
  1. Sample opening weekend from a log-normal distribution fit to (low, point, high)
  2. Decompose into Fri/Sat/Sun via industry-prior day shares (with noise)
  3. Sample weekday curve (Mon-Thu) using day-of-week multipliers (with noise)
  4. Apply a word-of-mouth modifier to weekdays (lower if RT < 50, higher if RT > 80)

Output a distribution over first-7-day totals + per-day percentiles.

Industry priors used here are domain-common rules of thumb. Sources:
  - Box Office Mojo daily reports for typical wide releases 2022-2024
  - The-Numbers historical data for sequel vs. original distinctions
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np

from .schemas import Film, FilmForecast, FirstWeekForecast


# Day-of-week multipliers expressed as fraction-of-Friday for typical wide release
# i.e., Saturday = 1.18 × Friday, etc.
# These have noise; (mean, std) for normal sampling
DEFAULT_DAY_MULTIPLIERS_VS_FRI = {
    "Fri": (1.00, 0.0),
    "Sat": (1.18, 0.06),
    "Sun": (0.78, 0.05),
    "Mon": (0.38, 0.06),
    "Tue": (0.36, 0.06),
    "Wed": (0.31, 0.05),
    "Thu": (0.34, 0.05),
}
DAY_NAMES = ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]


@dataclass
class MultiplierAdjustment:
    """Lets callers override day-of-week priors for genre/film-type effects."""
    sat_factor: float = 1.0  # multiplier on default Sat
    sun_factor: float = 1.0  # multiplier on default Sun
    weekday_factor: float = 1.0  # multiplier on default Mon-Thu (uniform)
    note: str = ""

    @classmethod
    def for_film(cls, film: Film) -> "MultiplierAdjustment":
        """Pick adjustments based on genre/franchise heuristics."""
        genre = " ".join(film.genre).lower() if film.genre else ""
        title = (film.title + " " + (film.franchise or "")).lower()
        # Animated family films tend to have stronger Sat boost (matinee)
        if "animat" in genre or "family" in genre or "illumination" in (film.studio or "").lower():
            return cls(sat_factor=1.05, sun_factor=1.04, weekday_factor=1.10,
                       note="animated/family: boosted Sat/Sun + stronger weekdays")
        # Horror is typically front-loaded — weak weekdays
        if "horror" in genre:
            return cls(sat_factor=0.95, sun_factor=0.92, weekday_factor=0.85,
                       note="horror: front-loaded, weaker weekdays")
        # Sequels tend to be slightly more front-loaded
        if film.sequel_number and film.sequel_number > 1:
            return cls(weekday_factor=0.92,
                       note=f"sequel #{film.sequel_number}: slightly front-loaded")
        return cls(note="default wide-release curve")


def _sample_opening_weekend(point: float, ci_low: float, ci_high: float, rng: np.random.Generator) -> float:
    """Sample from a log-normal that has the given point as median and ~80% mass between low and high.

    For an 80% CI on log-normal: log_low and log_high are at z=±1.28 from log_median.
    We compute log_std from the asymmetric CI by averaging both half-widths.
    """
    if point <= 0:
        point = max(1e6, ci_low)
    log_median = math.log(point)
    z = 1.2816  # 80% CI tail
    if ci_low <= 0:
        ci_low = point * 0.5
    if ci_high <= ci_low:
        ci_high = point * 1.5
    log_std = ((math.log(point) - math.log(ci_low)) + (math.log(ci_high) - math.log(point))) / (2 * z)
    log_std = max(0.05, log_std)  # guard
    sample = math.exp(rng.normal(log_median, log_std))
    return sample


def _sample_word_of_mouth(film: Film, rng: np.random.Generator) -> float:
    """Sample a multiplier that adjusts weekday performance based on quality signal.

    If RT score is known: high RT → boost weekday WoM, low RT → discount.
    If unknown: noise around 1.0.

    The WoM effect is gentler than the day-of-week curve — weekday gross still
    follows the prior, this just nudges it up/down based on quality reception.
    """
    if film.rotten_tomatoes_score is not None:
        rt = film.rotten_tomatoes_score
        # Linear map: RT=80 → +5%, RT=40 → -5%, RT=95 → +8%, RT=20 → -10%
        center = 1.0 + (rt - 60) / 400
        return float(rng.normal(center, 0.05))
    return float(rng.normal(1.0, 0.07))


def monte_carlo_first_week(
    film: Film,
    forecast: FilmForecast,
    n_samples: int = 5000,
    seed: int = 42,
    multiplier_adj: MultiplierAdjustment | None = None,
) -> FirstWeekForecast:
    """Monte Carlo first-week box office simulator.

    Returns a FirstWeekForecast with the distribution stats + per-day percentiles.
    """
    rng = np.random.default_rng(seed)
    if multiplier_adj is None:
        multiplier_adj = MultiplierAdjustment.for_film(film)

    # Per-day samples: shape (n_samples, 7)
    per_day = np.zeros((n_samples, 7), dtype=np.float64)
    week_totals = np.zeros(n_samples, dtype=np.float64)

    # Convention: opening weekend = Fri+Sat+Sun shares of the sampled OW
    # Within the weekend, default split: Fri 30%, Sat 38%, Sun 32% (a typical wide release)
    weekend_split_mean = np.array([0.30, 0.38, 0.32])
    weekend_split_noise = np.array([0.02, 0.02, 0.02])

    for i in range(n_samples):
        ow = _sample_opening_weekend(
            forecast.point_estimate_usd, forecast.ci_low_usd, forecast.ci_high_usd, rng
        )
        # Weekend split (with Dirichlet-ish noise)
        split = rng.normal(weekend_split_mean, weekend_split_noise)
        split = np.clip(split, 0.15, 0.55)
        split = split / split.sum()
        fri = ow * split[0]
        sat = ow * split[1] * multiplier_adj.sat_factor
        sun = ow * split[2] * multiplier_adj.sun_factor

        # Re-normalize so weekend total still equals OW
        weekend_now = fri + sat + sun
        if weekend_now > 0:
            scale = ow / weekend_now
            fri *= scale
            sat *= scale
            sun *= scale

        # Weekday curve: as fraction-of-Friday, with noise
        wom = _sample_word_of_mouth(film, rng)
        weekdays = []
        for d in ("Mon", "Tue", "Wed", "Thu"):
            mu, sd = DEFAULT_DAY_MULTIPLIERS_VS_FRI[d]
            mult = float(rng.normal(mu, sd)) * multiplier_adj.weekday_factor * wom
            mult = max(0.05, mult)
            weekdays.append(fri * mult)

        per_day[i] = [fri, sat, sun, *weekdays]
        week_totals[i] = per_day[i].sum()

    pct = lambda a, p: int(np.percentile(a, p))

    return FirstWeekForecast(
        film_id=film.id,
        n_samples=n_samples,
        first_week_median_usd=pct(week_totals, 50),
        first_week_p10_usd=pct(week_totals, 10),
        first_week_p25_usd=pct(week_totals, 25),
        first_week_p75_usd=pct(week_totals, 75),
        first_week_p90_usd=pct(week_totals, 90),
        day_medians_usd=[pct(per_day[:, d], 50) for d in range(7)],
        day_p10_usd=[pct(per_day[:, d], 10) for d in range(7)],
        day_p90_usd=[pct(per_day[:, d], 90) for d in range(7)],
        opening_weekend_used={
            "point": forecast.point_estimate_usd,
            "ci_low": forecast.ci_low_usd,
            "ci_high": forecast.ci_high_usd,
        },
        multiplier_assumptions={
            "day_multipliers_vs_fri": {k: v[0] for k, v in DEFAULT_DAY_MULTIPLIERS_VS_FRI.items()},
            "adjustment_note": multiplier_adj.note,
            "sat_factor": multiplier_adj.sat_factor,
            "sun_factor": multiplier_adj.sun_factor,
            "weekday_factor": multiplier_adj.weekday_factor,
        },
        word_of_mouth_modifier_used={
            "rotten_tomatoes_score": film.rotten_tomatoes_score,
            "model": ("RT-anchored" if film.rotten_tomatoes_score is not None else "neutral"),
        },
    )


def render_first_week_text(film: Film, fw: FirstWeekForecast) -> str:
    """Pretty-print the MC distribution as a markdown block."""
    lines = []
    lines.append(f"## {film.title} — first-week Monte Carlo (N={fw.n_samples:,})")
    lines.append("")
    lines.append(f"**Opening weekend used**: ${fw.opening_weekend_used['point']/1e6:.1f}M point, "
                 f"80% CI [${fw.opening_weekend_used['ci_low']/1e6:.1f}M, ${fw.opening_weekend_used['ci_high']/1e6:.1f}M]")
    lines.append(f"**Curve adjustment**: {fw.multiplier_assumptions['adjustment_note']}")
    lines.append("")
    lines.append(f"### First 7 days total")
    lines.append("")
    lines.append(f"| Percentile | First-week gross |")
    lines.append(f"|---|---|")
    for label, key in (("P10", "first_week_p10_usd"), ("P25", "first_week_p25_usd"),
                       ("Median", "first_week_median_usd"),
                       ("P75", "first_week_p75_usd"), ("P90", "first_week_p90_usd")):
        v = getattr(fw, key)
        lines.append(f"| {label} | ${v/1e6:.1f}M |")
    lines.append("")
    lines.append(f"### Per-day median (P50) and P10–P90 range")
    lines.append("")
    lines.append("| Day | Median | P10–P90 |")
    lines.append("|---|---|---|")
    for d in range(7):
        med = fw.day_medians_usd[d]
        lo = fw.day_p10_usd[d]
        hi = fw.day_p90_usd[d]
        lines.append(f"| {DAY_NAMES[d]} | ${med/1e6:.2f}M | [${lo/1e6:.2f}M, ${hi/1e6:.2f}M] |")
    return "\n".join(lines)
