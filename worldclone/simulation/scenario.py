"""Load the Iran 2026 scenario: timeline, actors, initial world state."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Actor:
    id: str
    name: str
    role: str
    public_position: str
    private_calculus: str
    drives: list[str]
    model_temperature: float = 0.9


@dataclass
class Scenario:
    cutoff_date: str
    facts: list[dict]  # [{"date": "YYYY-MM-DD", "fact": "...", "source": "..."}]
    actors: list[Actor]
    initial_world_state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path = "data/iran_timeline.json") -> "Scenario":
        with Path(path).open() as f:
            raw = json.load(f)
        actors = [Actor(**a) for a in raw["key_actors"]]
        return cls(
            cutoff_date=raw["_metadata"]["narrative_cutoff_date"],
            facts=[f for f in raw["facts"] if f["date"] <= raw["_metadata"]["narrative_cutoff_date"]],
            actors=actors,
            initial_world_state=dict(raw["initial_world_state"]),
            metadata=dict(raw["_metadata"]),
        )

    def timeline_block(self) -> str:
        """Render facts as a chronological text block for actor/GM prompts."""
        lines = []
        for f in self.facts:
            lines.append(f"{f['date']}: {f['fact']}")
        return "\n".join(lines)

    def actor_by_id(self, actor_id: str) -> Actor:
        for a in self.actors:
            if a.id == actor_id:
                return a
        raise KeyError(f"actor not found: {actor_id}")
