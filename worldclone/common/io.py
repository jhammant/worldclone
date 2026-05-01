"""Pydantic schemas for forecasts, simulation runs, scoring."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ManifoldQuestion(BaseModel):
    """One Iran-cluster market with everything needed to score."""
    id: str
    question: str
    url: str
    resolution: Literal["YES", "NO", "MKT", "CANCEL"] | None
    resolution_probability: float | None = None
    resolution_time_ms: int | None = None
    close_time_ms: int | None = None
    create_time_ms: int | None = None
    volume: float = 0.0
    unique_bettors: int = 0
    # Hand-curated fields
    resolution_criteria: str = ""
    questionnaire_key: str = ""  # short snake_case key used in the simulation questionnaire schema
    questionnaire_prompt: str = ""  # exact yes/no question phrased for the simulation observer

    @property
    def resolution_binary(self) -> int | None:
        if self.resolution == "YES":
            return 1
        if self.resolution == "NO":
            return 0
        return None  # MKT / CANCEL excluded from scoring


class TimelineFact(BaseModel):
    """One dated fact in the scenario seed."""
    date: str  # ISO YYYY-MM-DD
    fact: str
    source: str = ""


class ForecastResult(BaseModel):
    """One forecaster prediction for one question."""
    question_id: str
    probability: float = Field(ge=0.0, le=1.0)
    ensemble_probabilities: list[float] = Field(default_factory=list)
    reasoning: str = ""
    n_articles_used: int = 0
    queries: list[str] = Field(default_factory=list)
    model: str = ""
    elapsed_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SimulationRunOutcome(BaseModel):
    """Questionnaire result from one Monte Carlo run."""
    run_idx: int
    answers: dict[str, Literal["YES", "NO"]]
    final_state: dict
    elapsed_seconds: float = 0.0


class SimulationAggregate(BaseModel):
    """Aggregated probabilities across N simulation runs."""
    n_runs: int
    probabilities: dict[str, float]  # questionnaire_key -> P(YES)
    wilson_ci: dict[str, tuple[float, float]] = Field(default_factory=dict)
    model: str = ""
    elapsed_seconds: float = 0.0


class BrierScore(BaseModel):
    """Per-question + aggregate Brier."""
    per_question: dict[str, float]
    mean: float
    method: str = ""
