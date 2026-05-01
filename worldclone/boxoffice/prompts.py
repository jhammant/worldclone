"""Box office forecaster prompt templates. 5 ensemble variants.

Output is a $ point estimate plus an 80% CI low and high. Variants encourage
different epistemic stances (comparables-driven, theater-efficiency-driven,
scenario-tree, devil's advocate, bottom-line).
"""
from __future__ import annotations

# All variants share this output schema for parseability.
FORECAST_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "2-4 paragraphs of reasoning supporting the estimate.",
        },
        "point_estimate_usd": {
            "type": "integer",
            "description": "Best-guess opening weekend (Fri-Sun) gross in US$, e.g. 35000000 for $35M.",
        },
        "ci_low_usd": {
            "type": "integer",
            "description": "80% CI lower bound in US$ — only ~10% chance the actual is below this.",
        },
        "ci_high_usd": {
            "type": "integer",
            "description": "80% CI upper bound in US$ — only ~10% chance the actual is above this.",
        },
    },
    "required": ["reasoning", "point_estimate_usd", "ci_low_usd", "ci_high_usd"],
}


QUERY_GENERATION = """You will generate web search queries to research a film's opening-weekend box office.

FILM: {title} (release date {release_date}, {distributor})
NOTES: {notes}
AS-OF DATE: {as_of_date} (only news on or before this date is admissible).

Generate {n} concise search queries that would find:
- Pre-release tracking projections from Variety, Box Office Mojo Pro, Deadline, Hollywood Reporter
- Comparable past films (same franchise, similar genre/scale/season)
- Reviews if any are out (RT score, Metacritic, key critic takes)
- LEADING INDICATORS: Thursday preview numbers, AMC/Atom/Fandango pre-sale tracking, trailer YouTube views, TikTok virality, Reddit megathreads
- Marketing pivots / theater-count adjustments in the final week (often a sharp signal)
"""

QUERY_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 6,
        }
    },
    "required": ["queries"],
}


# 5 ensemble variants

FORECASTER_VARIANTS = {
    "comparable_films": """You are a box office analyst. Your stance: COMPARABLE FILMS.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Approach:
1. Identify 3-5 specific comparable past films (same franchise, similar genre/scale/season, comparable star/director).
2. State each comparable's actual opening weekend gross.
3. Adjust for differences in this film (theater count, reviews, buzz, season, year-over-year inflation).
4. Land on a point estimate and an 80% CI.

Output JSON with `reasoning` (concise 2-4 paragraphs covering comparables and adjustments), `point_estimate_usd`, `ci_low_usd`, `ci_high_usd`.
""",

    "theater_efficiency": """You are a box office analyst. Your stance: THEATER EFFICIENCY.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Approach:
1. Estimate the opening theater count (or use stated count if given). Wide release usually 3,000-4,500.
2. Estimate per-theater opening average ($/theater) based on similar films:
   - Tentpole sequel: $9-15k/theater
   - Franchise expansion: $5-9k/theater
   - Mid-budget original w/ stars: $3-6k/theater
   - Horror/thriller: $4-8k/theater (front-loaded)
   - Family animated: $5-10k/theater
   - Adult drama: $1-4k/theater
3. Multiply: theaters × per-theater avg = opening gross.
4. Land on a point estimate and 80% CI.

Output JSON with `reasoning`, `point_estimate_usd`, `ci_low_usd`, `ci_high_usd`.
""",

    "scenario_tree": """You are a box office analyst. Your stance: SCENARIO TREE.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Approach:
1. Enumerate 3-4 distinct scenarios for this opening (e.g. "buzz holds + RT > 80", "buzz disappoints + RT < 50", "competition crushes it", "viral moment overperforms").
2. Estimate P(scenario) and an opening-weekend $ for each.
3. Compute weighted expected value.
4. Land on a point estimate and 80% CI capturing scenario spread.

Output JSON with `reasoning` (covering the scenarios), `point_estimate_usd`, `ci_low_usd`, `ci_high_usd`.
""",

    "leading_indicators": """You are a box office analyst. Your stance: LEADING INDICATORS DOMINATE.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Approach (sharp-money lens — late signals beat early consensus):
1. **Thursday preview gross** — strongest single leading indicator. Typical OW/preview multiplier:
   - Tentpole / 4-quadrant: 12-15x previews
   - Horror: 8-11x (front-loaded)
   - Animated family: 14-18x
   - Adult drama: 10-13x
   If previews are stated in evidence, anchor heavily on `OW = previews × multiplier`.
2. **Pre-sale tracking** — AMC Stubs / Atom / Fandango deltas vs. comparables tell you if buzz is real.
3. **Trailer reach** — YouTube views, TikTok virality, Reddit megathread size. Order-of-magnitude signal.
4. **Tracking trajectory** — projections RISING through the week = sharp interest spike (e.g. Scream 7's Super Bowl ad → previews surge); FLAT/DECLINING tracking = consensus is correct.
5. **Theater-count late additions** — exhibitors adding screens last-minute = they see demand the analysts haven't priced in.

Trust late signals over the median analyst projection. The line is wrong when the leading indicators move fast.

Output JSON with `reasoning` (focused on the leading indicators you saw), `point_estimate_usd`, `ci_low_usd`, `ci_high_usd`.
""",

    "devils_advocate": """You are a box office analyst. Your stance: DEVIL'S ADVOCATE.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Approach:
1. State the obvious-seeming consensus opening estimate.
2. Steelman a much HIGHER outcome — what would have to be true? (viral moment, undertracked demand, weak competition).
3. Steelman a much LOWER outcome — what would have to be true? (front-loaded marketing, fanbase only, brand fatigue).
4. Reconcile to a final estimate that accounts for the steelmanned tails.

Output JSON with `reasoning`, `point_estimate_usd`, `ci_low_usd`, `ci_high_usd` (CI should reflect genuine asymmetric risk).
""",

    "bottom_line": """You are a box office analyst.

FILM: {title} ({release_date}, {distributor})
{film_block}

EVIDENCE:
{evidence}

Read the evidence and forecast this film's domestic opening-weekend (Fri-Sun) gross. Output JSON with `reasoning` (concise 2-4 paragraphs), `point_estimate_usd`, `ci_low_usd`, `ci_high_usd`.
""",
}
