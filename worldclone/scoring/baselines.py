"""Baseline probability sources to score against."""
from __future__ import annotations

from ..common.io import ManifoldQuestion


def community_close(q: ManifoldQuestion) -> float:
    """Manifold community probability at market close.

    `resolution_probability` is the implied probability at resolution per Manifold's
    resolutionProbability field. This is the strongest single baseline.
    """
    if q.resolution_probability is None:
        return 0.5
    return float(q.resolution_probability)


def naive_50() -> float:
    """Floor — every question gets 0.5."""
    return 0.5
