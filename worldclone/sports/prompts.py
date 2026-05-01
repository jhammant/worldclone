"""Sports game forecaster prompts. 5 ensemble variants.

Output: probability home wins + predicted margin (home perspective). Same
JSON-schema enforcement pattern as the box office forecaster.
"""
from __future__ import annotations

GAME_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "2-3 paragraphs of reasoning supporting the call.",
        },
        "p_home_win": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 0.99,
            "description": "Probability the home team wins.",
        },
        "predicted_margin_home": {
            "type": "number",
            "description": "Predicted final-score margin from the home team's perspective. Negative if home loses. E.g. 5.5 = home wins by 5-6, -3 = home loses by 3.",
        },
        "predicted_total": {
            "type": "number",
            "description": "Predicted total combined points scored.",
        },
    },
    "required": ["reasoning", "p_home_win", "predicted_margin_home"],
}


QUERY_GENERATION = """You generate web search queries to research a sports game forecast.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
CONTEXT: {context}
AS-OF DATE: {as_of_date} (only news on or before this date is admissible).

Generate {n} search queries that would surface:
- Vegas closing lines, sharp money movement
- Recent team form (last 5-10 games), key stats
- Injury reports, lineup changes
- Head-to-head history this season / playoff series state
- Public betting splits / consensus picks
"""

QUERY_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 6},
    },
    "required": ["queries"],
}


FORECASTER_VARIANTS = {
    "form_and_stats": """You are a sharp sports bettor. Your stance: RECENT FORM + STATS.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
{context}

EVIDENCE:
{evidence}

Approach:
1. State each team's recent form (last 5-10 games), home/away splits, head-to-head this season.
2. Identify the matchup-relevant statistical edge (offensive rating vs. defensive rating, pace, key player matchups).
3. Adjust for injuries / rest / travel.
4. Land on P(home wins) and predicted margin.

Output JSON with `reasoning` (concise), `p_home_win` (0.01-0.99), `predicted_margin_home`, `predicted_total`.
""",

    "vegas_anchored": """You are a sharp sports bettor. Your stance: ANCHOR ON THE LINE.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
{context}

EVIDENCE:
{evidence}

Approach:
1. State the closing or current Vegas line (moneyline, spread, total).
2. Compute the implied probability from the moneyline.
3. Identify any reasons to deviate from the line (injuries leaked late, weather changes, sharp money flips).
4. Be conservative — the line is hard to beat. Only deviate substantially when there's a specific identifiable edge.

Output JSON with `reasoning`, `p_home_win`, `predicted_margin_home`, `predicted_total`.
""",

    "playoff_dynamics": """You are a sharp sports bettor. Your stance: PLAYOFF/SERIES DYNAMICS.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
{context}

EVIDENCE:
{evidence}

Approach (skip this stance if game is regular season — defer to form_and_stats):
1. State the series score and game number; consider the "elimination effect" and "closeout difficulty."
2. Identify rotation/coaching adjustments expected after the previous game.
3. Consider home-court advantage in the playoffs (typically 2.5-3.5 points in the NBA, less in NHL).
4. Land on P(home wins) and margin.

Output JSON with `reasoning`, `p_home_win`, `predicted_margin_home`, `predicted_total`.
""",

    "devils_advocate": """You are a sharp sports bettor. Your stance: DEVIL'S ADVOCATE.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
{context}

EVIDENCE:
{evidence}

Approach:
1. State the obvious-seeming pick.
2. Steelman the opposite outcome — what's everyone overlooking? (e.g. tired favorite, motivated underdog, scheme advantage).
3. Reconcile to a probability that incorporates the steelman.

Output JSON with `reasoning`, `p_home_win`, `predicted_margin_home`, `predicted_total`.
""",

    "naive": """You are a sports forecaster.

GAME: {away_team} at {home_team} — {sport_label} {game_date}
{context}

EVIDENCE:
{evidence}

Read the evidence and forecast the game. Output JSON with `reasoning`, `p_home_win`, `predicted_margin_home`, `predicted_total`.
""",
}


SPORT_LABELS = {
    "nba": "NBA",
    "nfl": "NFL",
    "nhl": "NHL",
    "mlb": "MLB",
    "epl": "Premier League",
    "mls": "MLS",
    "ncaaf": "NCAA Football",
    "ncaab": "NCAA Basketball",
}
