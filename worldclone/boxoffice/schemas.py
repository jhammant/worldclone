"""Pydantic models for film releases and forecasts."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Film(BaseModel):
    """One wide release we want to forecast."""
    id: str  # slug like "minecraft-movie-2025"
    title: str
    release_date: str  # ISO YYYY-MM-DD (typically a Friday)
    distributor: str = ""
    studio: str = ""
    director: str = ""
    cast: list[str] = Field(default_factory=list)
    genre: list[str] = Field(default_factory=list)
    rating: Literal["G", "PG", "PG-13", "R", "NC-17", "Unrated"] | None = None
    runtime_minutes: int | None = None
    franchise: str | None = None  # e.g. "Marvel Cinematic Universe", "Wicked", "" if standalone
    sequel_number: int | None = None  # 1 = original, 2 = first sequel, etc.
    budget_usd: int | None = None  # production budget if known
    opening_theater_count: int | None = None  # if known by Tuesday before opening
    rotten_tomatoes_score: int | None = None  # 0-100, if reviews are out
    metacritic_score: int | None = None
    notes: str = ""

    plot_summary: str = ""
    franchise_priors: list[dict] = Field(default_factory=list)  # [{"title": "...", "release_date": "...", "opening_weekend_usd": int}]

    # Leading indicators (populate any that are known by the as-of date)
    thursday_previews_usd: int | None = None  # Thursday-night preview gross (the strongest single leading indicator)
    presales_signal: str = ""  # free-text — e.g. "AMC Stubs presales tracking 2x Wicked Pt1 at same point"
    trailer_youtube_views: int | None = None  # Cumulative views of the main official trailer at as-of date
    social_buzz_note: str = ""  # free-text social signal — TikTok virality, Reddit megathread activity, etc.

    # Ground truth — populated after release
    actual_opening_weekend_usd: int | None = None
    actual_opening_theaters: int | None = None
    actual_opening_per_theater_avg: float | None = None
    actual_first_week_usd: int | None = None  # Fri through following Thu (7 days)
    actual_per_day: dict[str, int] = Field(default_factory=dict)  # {"2026-04-03": 35000000, ...}


class FilmForecast(BaseModel):
    """One forecaster prediction for one film's opening weekend."""
    film_id: str
    point_estimate_usd: int  # best-guess opening weekend
    ci_low_usd: int  # 80% CI lower bound
    ci_high_usd: int  # 80% CI upper bound
    ensemble_estimates: list[int] = Field(default_factory=list)  # raw point estimates from each variant
    reasoning: str = ""
    n_articles_used: int = 0
    queries: list[str] = Field(default_factory=list)
    model: str = ""
    elapsed_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    as_of_date: str = ""  # forecast cutoff (typically Tuesday before Fri release)


class FirstWeekForecast(BaseModel):
    """Monte Carlo distribution over first 7 days of release."""
    film_id: str
    n_samples: int

    # Aggregate first-week statistics (USD)
    first_week_median_usd: int
    first_week_p10_usd: int
    first_week_p25_usd: int
    first_week_p75_usd: int
    first_week_p90_usd: int

    # Per-day medians (Fri, Sat, Sun, Mon, Tue, Wed, Thu)
    day_medians_usd: list[int] = Field(default_factory=list)
    day_p10_usd: list[int] = Field(default_factory=list)
    day_p90_usd: list[int] = Field(default_factory=list)

    # Underlying assumptions
    opening_weekend_used: dict = Field(default_factory=dict)  # {"point", "ci_low", "ci_high"}
    multiplier_assumptions: dict = Field(default_factory=dict)  # day-of-week multipliers used
    word_of_mouth_modifier_used: dict = Field(default_factory=dict)  # {"mean", "std"}

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
