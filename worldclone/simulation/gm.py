"""Game Master: adjudicate the round's actions, narrate, update world state.

Per step: takes the 6 actors' proposed actions + current world state, returns:
  - narrated event block
  - state delta (typed dict)
  - new "recent events" entries
"""
from __future__ import annotations

import json
from typing import Any

from .scenario import Scenario


# State fields we track. Stored in a flat dict for ease.
STATE_FIELDS = {
    "casualties_us_killed": "integer",
    "casualties_iran_killed_estimated": "integer",
    "us_ground_troops_in_iran": "boolean",
    "us_strikes_on_iran_infrastructure": "boolean",
    "us_nuclear_used": "boolean",
    "iran_nuclear_used": "boolean",
    "ceasefire_in_effect": "boolean",
}

# JSON schema for GM adjudication output
GM_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "narrative": {
            "type": "string",
            "description": "2-4 sentence narration of what happened this step in response to the actors' actions.",
        },
        "state_delta": {
            "type": "object",
            "properties": {
                "casualties_us_killed_delta": {"type": "integer", "description": "Additional US service members killed this step (>= 0)"},
                "casualties_iran_killed_estimated_delta": {"type": "integer", "description": "Additional Iranian deaths this step (>= 0)"},
                "us_ground_troops_in_iran": {"type": "boolean", "description": "Set TRUE the moment uniformed US ground troops physically enter Iranian soil under US gov't orders. Once true, stays true."},
                "us_strikes_on_iran_infrastructure": {"type": "boolean", "description": "TRUE only on direct US strike of civilian infrastructure (power, oil, transport, nuclear facilities). Does NOT trigger on military-only strikes. Once true, stays true."},
                "us_nuclear_used": {"type": "boolean", "description": "TRUE only if the US uses nuclear weapons against Iran. Once true, stays true."},
                "iran_nuclear_used": {"type": "boolean", "description": "TRUE only if Iran uses nuclear weapons. Once true, stays true."},
                "ceasefire_in_effect": {"type": "boolean", "description": "TRUE if a formal ceasefire is in effect. Can flip back to FALSE if it breaks down."},
                "us_aircraft_lost_event": {"type": "string", "description": "If a US manned aircraft was SHOT DOWN this step, brief description (e.g. 'F-15E shot down 2026-04-03'). Otherwise empty string. Damaged-but-emergency-landed aircraft do NOT count."},
            },
            "required": [
                "casualties_us_killed_delta",
                "casualties_iran_killed_estimated_delta",
                "us_ground_troops_in_iran",
                "us_strikes_on_iran_infrastructure",
                "us_nuclear_used",
                "iran_nuclear_used",
                "ceasefire_in_effect",
                "us_aircraft_lost_event",
            ],
        },
    },
    "required": ["narrative", "state_delta"],
}


def build_gm_messages(
    scenario: Scenario,
    current_date: str,
    world_state: dict[str, Any],
    proposals: list[tuple[str, dict]],  # [(actor_id, {"action": str, "reasoning": str})]
    recent_events: list[str],
) -> list[dict]:
    timeline = scenario.timeline_block()
    state_json = json.dumps(world_state, indent=2)
    events_block = "\n".join(f"- {e}" for e in recent_events[-12:]) if recent_events else "(none yet — opening turn)"

    proposals_block = "\n".join(
        f"- {actor_id}: {p['action']} | reasoning: {p['reasoning']}"
        for actor_id, p in proposals
    )

    system = f"""You are the GAME MASTER of a multi-agent simulation of US-Iran tensions in 2026.

Your job: given the actors' proposed actions for this step, adjudicate plausibly and update the world state.

Rules:
- Be GROUNDED. Iran cannot magically destroy a US carrier; the US cannot occupy Tehran in a week.
- Casualties accrue realistically — each step is roughly 3 narrative days.
- Resolution-relevant flags are STICKY: once `us_ground_troops_in_iran` is true, it stays true. Same for nuclear use, infrastructure strikes.
- BE STRICT about flag definitions: `us_strikes_on_iran_infrastructure` is FALSE for strikes on purely military targets. `us_ground_troops_in_iran` requires uniformed US service members under US gov't orders — contractors and accidental crossings do NOT count.
- The current ceasefire status can change in either direction.
- When in doubt, DO NOT flip a flag — flag-flips need explicit, decisive action.

You are a judge, not an actor. You do not have your own goals.
"""

    user = f"""Background timeline through 2026-03-28:
{timeline}

Current date: {current_date}

Current world state:
{state_json}

Recent events this simulation:
{events_block}

Actors' proposed actions this step:
{proposals_block}

Adjudicate. Output JSON with:
- `narrative`: 2-4 sentences describing what happens this step.
- `state_delta`: integer deltas for casualty fields, current boolean values for sticky flags, and `us_aircraft_lost_event` (a string — only fill if a manned US aircraft was SHOT DOWN this step, otherwise empty).
"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def apply_state_delta(state: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Apply GM-emitted delta to current state. Returns new state.
    Sticky booleans only flip true→true (cannot un-do); ceasefire can flip both ways.
    """
    new = dict(state)
    new["casualties_us_killed"] = state.get("casualties_us_killed", 0) + max(0, int(delta.get("casualties_us_killed_delta", 0)))
    new["casualties_iran_killed_estimated"] = state.get("casualties_iran_killed_estimated", 0) + max(0, int(delta.get("casualties_iran_killed_estimated_delta", 0)))

    # Sticky-true flags
    for f in ("us_ground_troops_in_iran", "us_strikes_on_iran_infrastructure", "us_nuclear_used", "iran_nuclear_used"):
        new[f] = bool(state.get(f, False)) or bool(delta.get(f, False))

    # Mutable
    new["ceasefire_in_effect"] = bool(delta.get("ceasefire_in_effect", state.get("ceasefire_in_effect", False)))

    # Append aircraft-lost events
    aircraft_lost = list(state.get("us_aircraft_lost_to_iran", []))
    aircraft_event = delta.get("us_aircraft_lost_event", "")
    if aircraft_event and aircraft_event.strip():
        aircraft_lost.append(aircraft_event.strip())
    new["us_aircraft_lost_to_iran"] = aircraft_lost

    return new
