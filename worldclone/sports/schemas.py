"""Pydantic models for sports game forecasting."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SportLiteral = Literal["nba", "nfl", "nhl", "mlb", "epl", "mls", "ncaaf", "ncaab"]


class Game(BaseModel):
    """One sports game we want to forecast."""
    id: str  # slug like "nba-2026-04-29-bos-vs-mia"
    sport: SportLiteral
    season: str  # e.g. "2025-26"
    game_date: str  # ISO YYYY-MM-DD
    home_team: str
    away_team: str
    home_team_short: str = ""  # e.g. "BOS"
    away_team_short: str = ""
    is_playoff: bool = False
    series_context: str = ""  # e.g. "Game 5, Heat lead 3-1"
    venue: str = ""

    # Optional pre-game signals — populated if known by tip-off
    home_record_wins: int | None = None
    home_record_losses: int | None = None
    away_record_wins: int | None = None
    away_record_losses: int | None = None
    vegas_home_moneyline: int | None = None  # American odds, e.g. -150 / +130
    vegas_away_moneyline: int | None = None
    vegas_draw_moneyline: int | None = None  # 3-way market (soccer); None for binary sports
    vegas_spread: float | None = None  # Negative if home favored
    vegas_total: float | None = None  # over/under

    notes: str = ""

    # Ground truth — populated after the game
    actual_home_score: int | None = None
    actual_away_score: int | None = None
    actual_winner: Literal["home", "away", "draw"] | None = None

    @property
    def actual_margin_home(self) -> int | None:
        """Actual home-team margin (negative if home lost)."""
        if self.actual_home_score is None or self.actual_away_score is None:
            return None
        return self.actual_home_score - self.actual_away_score


class GameForecast(BaseModel):
    """Forecaster prediction for one game."""
    game_id: str
    p_home_win: float = Field(ge=0.0, le=1.0)
    predicted_margin_home: float  # positive = home wins by N points
    predicted_total: float | None = None  # combined points (over/under target)
    ensemble_p_home: list[float] = Field(default_factory=list)
    ensemble_margin: list[float] = Field(default_factory=list)
    reasoning: str = ""
    n_articles_used: int = 0
    queries: list[str] = Field(default_factory=list)
    model: str = ""
    elapsed_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    as_of_date: str = ""
