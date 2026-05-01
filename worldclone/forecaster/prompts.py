"""Forecaster prompt templates. 5 ensemble variants per Halawi et al. 2024.

Open-weights models (Qwen 3.6) tend to anchor harder on retrieved evidence than
Sonnet — devil's-advocate matters more here.
"""
from __future__ import annotations

QUERY_GENERATION = """You will be given a forecasting question. Generate {n} concise web search queries that would help you find information to forecast it.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (only news on or before this date is admissible).

Output JSON only.
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


RELEVANCE_BATCH = """Rate each article's relevance to the forecasting question on a scale 0-10.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}

Articles to rate:
{articles_block}

Return a JSON list with one entry per article in the same order, each with the article's index and an integer 0-10 score.
"""

RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 10},
                },
                "required": ["index", "score"],
            },
        }
    },
    "required": ["scores"],
}


SUMMARIZE = """Summarize the article in 2-3 sentences focused on what it tells us about the forecasting question.

QUESTION: {question}

ARTICLE:
{article}

Output the summary text only — no preamble.
"""


# 5 ensemble variants — diverse epistemic stances per Halawi (2024).
# All variants use the same JSON output schema so we can parse reliably.

FORECASTER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "2-4 paragraphs of reasoning supporting the probability.",
        },
        "probability": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 0.99,
            "description": "Your final probability that the question resolves YES.",
        },
    },
    "required": ["probability", "reasoning"],
}


FORECASTER_VARIANTS = {
    "base_rate": """You are a calibrated forecaster. Your stance: ANCHOR ON BASE RATES.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (do not use information from after this date).

EVIDENCE:
{evidence}

Approach:
1. What is the historical base rate for events of this type?
2. How should the specific evidence shift you from the base rate?
3. State your final probability.

Output JSON with `reasoning` (concise — 2-4 paragraphs) and `probability` (0.01-0.99).
""",

    "inside_view": """You are a calibrated forecaster. Your stance: INSIDE VIEW.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (do not use information from after this date).

EVIDENCE:
{evidence}

Approach:
1. Identify specific actors, mechanisms, incentives.
2. Trace the most likely causal path to YES and to NO.
3. Weight each path by plausibility given the evidence.
4. State your final probability.

Output JSON with `reasoning` (concise — 2-4 paragraphs) and `probability` (0.01-0.99).
""",

    "scenario_tree": """You are a calibrated forecaster. Your stance: SCENARIO TREE.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (do not use information from after this date).

EVIDENCE:
{evidence}

Approach:
1. Enumerate 3-4 distinct scenarios that could play out from the as-of date forward.
2. Estimate P(scenario) and P(YES | scenario) for each.
3. Compute P(YES) = sum over scenarios of P(scenario) * P(YES | scenario).
4. State your final probability.

Output JSON with `reasoning` (concise — 2-4 paragraphs covering the scenarios) and `probability` (0.01-0.99).
""",

    "devils_advocate": """You are a calibrated forecaster. Your stance: DEVIL'S ADVOCATE.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (do not use information from after this date).

EVIDENCE:
{evidence}

Approach:
1. State the obvious-seeming answer and the consensus probability someone might give.
2. Steelman the OPPOSITE answer. What would have to be true? What might the consensus be missing?
3. Reconcile and arrive at a final probability that accounts for the steelman.
4. State your final probability.

Output JSON with `reasoning` (concise — 2-4 paragraphs) and `probability` (0.01-0.99).
""",

    "naive": """You are a calibrated forecaster.

QUESTION: {question}
RESOLUTION CRITERIA: {criteria}
AS-OF DATE: {as_of_date} (do not use information from after this date).

EVIDENCE:
{evidence}

Read the evidence and forecast the question. Output JSON with `reasoning` (concise — 2-4 paragraphs) and `probability` (0.01-0.99).
""",
}
