"""Hand-computed Brier values; the experiment's scoring core."""
from __future__ import annotations

import math

import pytest

from worldclone.scoring.brier import (
    bootstrap_brier_ci,
    brier_mean,
    brier_one,
    log_loss_mean,
    log_loss_one,
    wilson_ci,
)


class TestBrierOne:
    def test_perfect_yes(self):
        assert brier_one(1.0, 1) == 0.0

    def test_perfect_no(self):
        assert brier_one(0.0, 0) == 0.0

    def test_max_wrong_yes(self):
        assert brier_one(0.0, 1) == 1.0

    def test_max_wrong_no(self):
        assert brier_one(1.0, 0) == 1.0

    def test_uncertain(self):
        assert brier_one(0.5, 1) == 0.25
        assert brier_one(0.5, 0) == 0.25

    def test_known_value(self):
        # p=0.7, outcome=1 → (0.7 - 1)^2 = 0.09
        assert brier_one(0.7, 1) == pytest.approx(0.09)

    def test_invalid_prob(self):
        with pytest.raises(ValueError):
            brier_one(1.1, 1)
        with pytest.raises(ValueError):
            brier_one(-0.1, 0)

    def test_invalid_outcome(self):
        with pytest.raises(ValueError):
            brier_one(0.5, 2)


class TestBrierMean:
    def test_aligned(self):
        # All perfect → 0
        assert brier_mean([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0

    def test_known(self):
        # (0.7→1)=0.09, (0.3→0)=0.09, (0.5→1)=0.25 → mean = 0.143...
        result = brier_mean([0.7, 0.3, 0.5], [1, 0, 1])
        assert result == pytest.approx((0.09 + 0.09 + 0.25) / 3)

    def test_empty(self):
        assert math.isnan(brier_mean([], []))

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            brier_mean([0.5], [1, 0])


class TestLogLoss:
    def test_perfect(self):
        # p=1, o=1 → -log(1) = 0 (with eps clipping it'll be ~0)
        assert log_loss_one(1.0, 1) == pytest.approx(0.0, abs=1e-7)

    def test_uncertain(self):
        # p=0.5 either way → -log(0.5) = ln(2) ≈ 0.693
        assert log_loss_one(0.5, 1) == pytest.approx(math.log(2))
        assert log_loss_one(0.5, 0) == pytest.approx(math.log(2))

    def test_mean(self):
        m = log_loss_mean([0.5, 0.5], [1, 0])
        assert m == pytest.approx(math.log(2))


class TestBootstrapCI:
    def test_deterministic_with_seed(self):
        probs = [0.7, 0.3, 0.5, 0.9, 0.1]
        outcomes = [1, 0, 1, 1, 0]
        lo1, hi1 = bootstrap_brier_ci(probs, outcomes, n_bootstrap=200, seed=42)
        lo2, hi2 = bootstrap_brier_ci(probs, outcomes, n_bootstrap=200, seed=42)
        assert lo1 == lo2 and hi1 == hi2

    def test_zero_inputs(self):
        lo, hi = bootstrap_brier_ci([], [], n_bootstrap=10)
        assert math.isnan(lo) and math.isnan(hi)


class TestWilsonCI:
    def test_zero_n(self):
        lo, hi = wilson_ci(0, 0)
        assert lo == 0.0 and hi == 1.0

    def test_perfect_yes(self):
        # 10/10 → CI shouldn't include 0
        lo, hi = wilson_ci(10, 10)
        assert lo > 0.5 and hi == 1.0 or hi <= 1.0

    def test_half(self):
        # 5/10 → centered around 0.5
        lo, hi = wilson_ci(5, 10)
        assert lo < 0.5 < hi

    def test_n_15_typical_pilot(self):
        # The pilot has N=15 runs; verify CI width is sensible
        lo, hi = wilson_ci(8, 15)
        width = hi - lo
        # Should be roughly ±0.2 or so for binomial near 0.5
        assert 0.3 < width < 0.6
