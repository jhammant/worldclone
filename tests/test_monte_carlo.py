"""Unit tests for the box office Monte Carlo simulator."""
from __future__ import annotations

import pytest

from worldclone.boxoffice.monte_carlo import (
    MultiplierAdjustment,
    monte_carlo_first_week,
)
from worldclone.boxoffice.schemas import Film, FilmForecast


def _film(**overrides):
    base = dict(id="t", title="Test Film", release_date="2026-04-01")
    base.update(overrides)
    return Film(**base)


def _forecast(point=100_000_000, lo=80_000_000, hi=120_000_000):
    return FilmForecast(
        film_id="t",
        point_estimate_usd=point,
        ci_low_usd=lo,
        ci_high_usd=hi,
    )


class TestMonteCarloShape:
    def test_returns_seven_day_distribution(self):
        fw = monte_carlo_first_week(_film(), _forecast(), n_samples=500, seed=1)
        assert fw.n_samples == 500
        assert len(fw.day_medians_usd) == 7
        assert len(fw.day_p10_usd) == 7
        assert len(fw.day_p90_usd) == 7

    def test_percentiles_ordered(self):
        fw = monte_carlo_first_week(_film(), _forecast(), n_samples=500, seed=1)
        assert fw.first_week_p10_usd <= fw.first_week_p25_usd
        assert fw.first_week_p25_usd <= fw.first_week_median_usd
        assert fw.first_week_median_usd <= fw.first_week_p75_usd
        assert fw.first_week_p75_usd <= fw.first_week_p90_usd

    def test_first_week_greater_than_opening_weekend(self):
        # First-week (7 days) total should always exceed opening weekend point estimate
        fc = _forecast(point=100_000_000, lo=80_000_000, hi=120_000_000)
        fw = monte_carlo_first_week(_film(), fc, n_samples=2000, seed=1)
        # Median first-week should be ~1.4x of opening point — not less than 1.0
        ratio = fw.first_week_median_usd / fc.point_estimate_usd
        assert 1.25 < ratio < 1.65, f"expected ~1.4 first-week multiplier, got {ratio:.2f}"

    def test_per_day_ordering_typical(self):
        # Sat should be biggest day; Wed should be smallest
        fw = monte_carlo_first_week(_film(), _forecast(), n_samples=2000, seed=1)
        fri, sat, sun, mon, tue, wed, thu = fw.day_medians_usd
        assert sat > fri, "Sat should beat Fri"
        assert sat > sun, "Sat should beat Sun"
        assert wed <= min(mon, tue, thu) * 1.05, "Wed should be one of the lowest weekdays"

    def test_deterministic_with_seed(self):
        fw1 = monte_carlo_first_week(_film(), _forecast(), n_samples=500, seed=42)
        fw2 = monte_carlo_first_week(_film(), _forecast(), n_samples=500, seed=42)
        assert fw1.first_week_median_usd == fw2.first_week_median_usd


class TestMultiplierAdjustment:
    def test_animated_film_gets_boosted_curve(self):
        animated = _film(genre=["Animation", "Family"])
        adj = MultiplierAdjustment.for_film(animated)
        assert adj.weekday_factor > 1.0, "animated should boost weekdays"

    def test_horror_film_gets_front_loaded(self):
        horror = _film(genre=["Horror"])
        adj = MultiplierAdjustment.for_film(horror)
        assert adj.weekday_factor < 1.0, "horror should weaken weekdays"

    def test_sequel_slightly_front_loaded(self):
        sequel = _film(sequel_number=2)
        adj = MultiplierAdjustment.for_film(sequel)
        assert adj.weekday_factor < 1.0


class TestRTAdjustment:
    def test_high_rt_pushes_first_week_up(self):
        # Same OW forecast; one with RT=90, one with RT=30
        film_good = _film(rotten_tomatoes_score=90)
        film_bad = _film(id="t2", rotten_tomatoes_score=30)
        good = monte_carlo_first_week(film_good, _forecast(), n_samples=2000, seed=1)
        bad = monte_carlo_first_week(film_bad, _forecast(), n_samples=2000, seed=1)
        assert good.first_week_median_usd > bad.first_week_median_usd

    def test_no_rt_neutral(self):
        # Without RT, modifier centered at 1.0 — first-week median near typical
        fw = monte_carlo_first_week(_film(), _forecast(), n_samples=2000, seed=1)
        ratio = fw.first_week_median_usd / 100_000_000
        assert 1.30 < ratio < 1.55
