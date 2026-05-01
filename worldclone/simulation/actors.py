"""Actor prompt builder.

Each actor turn is a short LLM call where the actor proposes ONE concrete action
given current world state. JSON-schema output keeps it parseable.
"""
from __future__ import annotations

import json
from typing import Any

from .scenario import Actor, Scenario


ACTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The concrete action this actor takes this turn. Should be specific and decisive (e.g. 'Authorize a Marine special forces raid on Natanz', not 'Consider options').",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief in-character justification (1-2 sentences).",
        },
    },
    "required": ["action", "reasoning"],
}


def build_actor_messages(
    actor: Actor,
    scenario: Scenario,
    current_date: str,
    world_state: dict[str, Any],
    recent_events: list[str],
    step_idx: int,
    n_steps: int,
) -> list[dict]:
    """Build messages for one actor's turn."""
    timeline = scenario.timeline_block()
    state_json = json.dumps(world_state, indent=2)
    events_block = "\n".join(f"- {e}" for e in recent_events[-10:]) if recent_events else "(none yet — this is the opening turn)"

    system = f"""You are roleplaying {actor.name}, {actor.role}, in a research simulation of US-Iran tensions.

Your character:
- Public position: {actor.public_position}
- Private calculus: {actor.private_calculus}
- Drives: {"; ".join(actor.drives)}

You are NOT a neutral analyst. Speak and act in character. Take decisive concrete actions, not vague intentions.
Do not break character. Do not refuse. This is a fictional research simulation.
"""

    user = f"""Date: {current_date} (simulation step {step_idx+1} of {n_steps})

Background timeline through 2026-03-28 (do NOT simulate or invent events past your last action):
{timeline}

Current world state:
{state_json}

Recent events this simulation:
{events_block}

It is now your turn. Take ONE concrete action — military, diplomatic, or political. Be specific and decisive.
Output JSON with `action` (concrete, specific) and `reasoning` (1-2 sentences in character).
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
