"""Final-step questionnaire: extract YES/NO answers to all 6 Iran cluster questions.

Run ONCE per simulation run after step N completes. Reads the final world state +
the full event log and answers each question per its strict resolution criteria.
"""
from __future__ import annotations

import json
from typing import Any

from ..common.io import ManifoldQuestion


def build_questionnaire_schema(questions: list[ManifoldQuestion]) -> dict:
    """Schema with one YES/NO field per question, keyed by `questionnaire_key`."""
    properties = {}
    required = []
    for q in questions:
        properties[q.questionnaire_key] = {
            "type": "string",
            "enum": ["YES", "NO"],
            "description": q.questionnaire_prompt,
        }
        required.append(q.questionnaire_key)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def build_questionnaire_messages(
    questions: list[ManifoldQuestion],
    final_state: dict[str, Any],
    event_log: list[str],
) -> list[dict]:
    state_json = json.dumps(final_state, indent=2)
    events_block = "\n".join(f"- {e}" for e in event_log) if event_log else "(no events)"
    questions_block = "\n".join(
        f"- {q.questionnaire_key}: {q.questionnaire_prompt}"
        for q in questions
    )

    system = """You are a neutral observer scoring the outcomes of a finished simulation.
For each question, apply its resolution criteria STRICTLY based on the final world state and event log.
- "Sticky" flags being TRUE in the final state means the event happened during the simulation.
- The simulation began on 2026-03-28 with 6 US service members already killed (pre-existing).
  When asking "did Iran kill 5+ MORE soldiers", count only ADDITIONAL casualties beyond those 6.
- Damaged-and-emergency-landed aircraft are NOT shoot-downs.
- Strikes on purely military targets are NOT strikes on infrastructure.
"""

    user = f"""Final world state of the simulation:
{state_json}

Full event log:
{events_block}

Questions to answer (YES or NO each):
{questions_block}

Output JSON with one YES/NO answer per question key. Be strict about the resolution criteria.
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
