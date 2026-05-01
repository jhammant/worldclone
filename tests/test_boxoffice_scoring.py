"""Hand-computed box office scoring tests."""
from __future__ import annotations

import math

import pytest

from worldclone.scoring.boxoffice import (
    absolute_percentage_error,
    baseline_median_opening,
    ci_coverage,
    log_absolute_error,
    log_mae,
    mape,
    median_ape,
    within_pct,
)


class TestAPE:
    def test_perfect(self):
        assert absolute_percentage_error(20_000_000, 20_000_000) == 0.0

    def test_known(self):
        # predicted $25M, actual $20M → APE 0.25
        assert absolute_percentage_error(25_000_000, 20_000_000) == pytest.approx(0.25)

    def test_underestimate(self):
        # predicted $15M, actual $20M → APE 0.25
        assert absolute_percentage_error(15_000_000, 20_000_000) == pytest.approx(0.25)

    def test_zero_actual_raises(self):
        with pytest.raises(ValueError):
            absolute_percentage_error(10, 0)


class TestMAPE:
    def test_basic(self):
        # APEs: 0.25, 0.10, 0.30 → mean = 0.2167
        m = mape([25e6, 11e6, 13e6], [20e6, 10e6, 10e6])
        assert m == pytest.approx((0.25 + 0.10 + 0.30) / 3, abs=1e-9)

    def test_empty(self):
        assert math.isnan(mape([], []))

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            mape([1.0], [1.0, 2.0])


class TestMedianAPE:
    def test_basic(self):
        # APEs: 0.25, 0.10, 0.30 → median 0.25
        m = median_ape([25e6, 11e6, 13e6], [20e6, 10e6, 10e6])
        assert m == pytest.approx(0.25)


class TestLogAE:
    def test_perfect(self):
        assert log_absolute_error(50_000_000, 50_000_000) == 0.0

    def test_two_x(self):
        # 10M predicted, 20M actual → log10(10M)=7, log10(20M)=7.301 → log_ae ≈ 0.301
        assert log_absolute_error(10_000_000, 20_000_000) == pytest.approx(0.30103, abs=1e-4)

    def test_half(self):
        # 20M predicted, 10M actual → same magnitude
        assert log_absolute_error(20_000_000, 10_000_000) == pytest.approx(0.30103, abs=1e-4)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            log_absolute_error(0, 1e6)


class TestWithinPct:
    def test_all_within(self):
        # all APEs < 0.30
        f = within_pct([22e6, 24e6, 18e6], [20e6, 20e6, 20e6], 0.30)
        assert f == 1.0

    def test_none_within(self):
        f = within_pct([200e6], [10e6], 0.20)
        assert f == 0.0

    def test_mixed(self):
        # APEs: 0.25, 0.10, 0.30 — within 0.20 hits: just one (0.10)
        f = within_pct([25e6, 11e6, 13e6], [20e6, 10e6, 10e6], 0.20)
        assert f == pytest.approx(1 / 3)


class TestCICoverage:
    def test_all_covered(self):
        f = ci_coverage([8e6, 15e6], [12e6, 25e6], [10e6, 20e6])
        assert f == 1.0

    def test_none_covered(self):
        f = ci_coverage([8e6, 15e6], [9e6, 18e6], [20e6, 100e6])
        assert f == 0.0

    def test_partial(self):
        # 1 covered, 1 not
        f = ci_coverage([8e6, 100e6], [12e6, 200e6], [10e6, 20e6])
        assert f == 0.5


class TestBaseline:
    def test_median(self):
        m = baseline_median_opening([5e6, 20e6, 50e6])
        assert m == 20e6
