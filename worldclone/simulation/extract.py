"""Aggregate Monte Carlo runs into per-question probabilities with Wilson CI."""
from __future__ import annotations

from typing import Any

from ..common.io import ManifoldQuestion, SimulationAggregate
from ..scoring.brier import wilson_ci


def aggregate(
    runs: list[dict[str, Any]],
    questions: list[ManifoldQuestion],
    model_name: str = "",
) -> SimulationAggregate:
    n = len(runs)
    probs = {}
    cis = {}
    for q in questions:
        k = q.questionnaire_key
        yes_count = sum(1 for r in runs if r["answers"].get(k) == "YES")
        probs[k] = yes_count / n if n > 0 else 0.5
        cis[k] = wilson_ci(yes_count, n)
    return SimulationAggregate(
        n_runs=n,
        probabilities=probs,
        wilson_ci=cis,
        model=model_name,
        elapsed_seconds=sum(r.get("elapsed_seconds", 0.0) for r in runs),
    )
