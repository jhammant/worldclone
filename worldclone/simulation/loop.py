"""Monte Carlo simulation loop. The thin core that ties actors + GM + questionnaire."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ..common import llm
from ..common.io import ManifoldQuestion
from .actors import ACTOR_OUTPUT_SCHEMA, build_actor_messages
from .gm import GM_OUTPUT_SCHEMA, apply_state_delta, build_gm_messages
from .questionnaire import build_questionnaire_messages, build_questionnaire_schema
from .scenario import Scenario

log = logging.getLogger(__name__)


async def run_one(
    *,
    scenario: Scenario,
    questions: list[ManifoldQuestion],
    n_steps: int,
    days_per_step: int,
    run_idx: int,
    seed: int,
    actor_max_tokens: int = 350,
    gm_max_tokens: int = 700,
    questionnaire_max_tokens: int = 400,
) -> dict[str, Any]:
    """Play out one Monte Carlo run. Returns dict with answers, final_state, log."""
    rng = random.Random(seed)
    state: dict[str, Any] = dict(scenario.initial_world_state)
    event_log: list[str] = []
    actor_props_log: list[dict] = []  # full per-step record for debugging
    cutoff = date.fromisoformat(scenario.cutoff_date)

    t0 = time.time()
    for step_idx in range(n_steps):
        current_date = (cutoff + timedelta(days=days_per_step * (step_idx + 1))).isoformat()
        actors = list(scenario.actors)
        rng.shuffle(actors)

        # Actor turns — parallel-batched (semaphore = parallel=2 in llm.py)
        actor_calls = [
            {
                "messages": build_actor_messages(
                    actor=a, scenario=scenario, current_date=current_date,
                    world_state=state, recent_events=event_log,
                    step_idx=step_idx, n_steps=n_steps,
                ),
                "schema": ACTOR_OUTPUT_SCHEMA,
                "max_tokens": actor_max_tokens,
                "reasoning_effort": "none",
                "temperature": a.model_temperature,
            }
            for a in actors
        ]
        results = await asyncio.gather(*[llm.chat_json(**c) for c in actor_calls], return_exceptions=True)

        proposals: list[tuple[str, dict]] = []
        for actor, result in zip(actors, results, strict=True):
            if isinstance(result, BaseException):
                log.warning("actor %s call failed step %d: %s", actor.id, step_idx, result)
                proposals.append((actor.id, {"action": "(no action — call failed)", "reasoning": ""}))
                continue
            parsed, _ = result
            proposals.append((actor.id, parsed))

        # GM adjudication — single call
        try:
            gm_parsed, _ = await llm.chat_json(
                messages=build_gm_messages(
                    scenario=scenario, current_date=current_date,
                    world_state=state, proposals=proposals, recent_events=event_log,
                ),
                schema=GM_OUTPUT_SCHEMA,
                max_tokens=gm_max_tokens,
                reasoning_effort="none",
                temperature=0.6,
            )
        except Exception as e:
            log.error("GM call failed step %d run %d: %s — using NOOP delta", step_idx, run_idx, e)
            gm_parsed = {
                "narrative": f"(GM call failed: {e})",
                "state_delta": {
                    "casualties_us_killed_delta": 0,
                    "casualties_iran_killed_estimated_delta": 0,
                    "us_ground_troops_in_iran": False,
                    "us_strikes_on_iran_infrastructure": False,
                    "us_nuclear_used": False,
                    "iran_nuclear_used": False,
                    "ceasefire_in_effect": state.get("ceasefire_in_effect", False),
                    "us_aircraft_lost_event": "",
                },
            }

        narrative = gm_parsed["narrative"]
        delta = gm_parsed["state_delta"]
        state = apply_state_delta(state, delta)

        event_log.append(f"[step {step_idx+1} | {current_date}] {narrative}")
        actor_props_log.append({
            "step": step_idx + 1,
            "date": current_date,
            "proposals": [{"actor": a, **p} for a, p in proposals],
            "narrative": narrative,
            "delta": delta,
            "state_after": dict(state),
        })

    # Final questionnaire
    try:
        q_parsed, _ = await llm.chat_json(
            messages=build_questionnaire_messages(questions, state, event_log),
            schema=build_questionnaire_schema(questions),
            max_tokens=questionnaire_max_tokens,
            reasoning_effort="none",
            temperature=0.2,
        )
        answers = {k: ("YES" if v == "YES" else "NO") for k, v in q_parsed.items()}
    except Exception as e:
        log.error("Questionnaire call failed run %d: %s", run_idx, e)
        # Fall back to a state-derived heuristic
        answers = _derive_answers_from_state(questions, state, event_log)

    elapsed = time.time() - t0
    return {
        "run_idx": run_idx,
        "seed": seed,
        "elapsed_seconds": elapsed,
        "final_state": state,
        "answers": answers,
        "event_log": event_log,
        "step_log": actor_props_log,
    }


def _derive_answers_from_state(
    questions: list[ManifoldQuestion],
    state: dict[str, Any],
    event_log: list[str],
) -> dict[str, str]:
    """Fallback if the questionnaire call fails — read the world state directly.
    This is conservative; the LLM questionnaire is preferred."""
    out = {}
    for q in questions:
        k = q.questionnaire_key
        if "ground_troops" in k or "boots_on_ground" in k:
            out[k] = "YES" if state.get("us_ground_troops_in_iran") else "NO"
        elif "nukes_iran" in k or "nuclear" in k:
            out[k] = "YES" if state.get("us_nuclear_used") else "NO"
        elif "infrastructure" in k:
            out[k] = "YES" if state.get("us_strikes_on_iran_infrastructure") else "NO"
        elif "shoots_down" in k or "aircraft" in k:
            out[k] = "YES" if state.get("us_aircraft_lost_to_iran") else "NO"
        elif "kills_5plus" in k:
            additional = state.get("casualties_us_killed", 6) - 6
            out[k] = "YES" if additional >= 5 else "NO"
        else:
            out[k] = "NO"
    return out


async def run_simulation(
    *,
    scenario: Scenario,
    questions: list[ManifoldQuestion],
    n_runs: int,
    n_steps: int,
    days_per_step: int = 3,
    out_dir: Path,
    base_seed: int = 42,
) -> list[dict[str, Any]]:
    """Run N Monte Carlo simulations sequentially. Each run is independent.

    We run sequentially (not parallel-runs) because LM Studio's parallel=2 budget
    is already consumed by per-step actor batching. Running multiple runs in parallel
    would just queue up at the LLM endpoint.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    # Resume support — load any runs that already finished
    results: list[dict[str, Any]] = []
    for i in range(n_runs):
        existing = runs_dir / f"run_{i:03d}.json"
        if existing.exists():
            try:
                with existing.open() as f:
                    results.append(json.load(f))
                log.info("=== Run %d/%d already completed — loaded from %s ===", i + 1, n_runs, existing)
                continue
            except Exception as e:
                log.warning("Could not load existing %s (%s); will re-run", existing, e)

        log.info("=== Run %d/%d (n_steps=%d) ===", i + 1, n_runs, n_steps)
        result = await run_one(
            scenario=scenario,
            questions=questions,
            n_steps=n_steps,
            days_per_step=days_per_step,
            run_idx=i,
            seed=base_seed + i,
        )
        results.append(result)
        # Persist incrementally
        with (runs_dir / f"run_{i:03d}.json").open("w") as f:
            json.dump(result, f, indent=2, default=str)
        with (out_dir / "checkpoint.jsonl").open("a") as f:
            f.write(json.dumps({
                "run_idx": i, "elapsed_seconds": result["elapsed_seconds"],
                "answers": result["answers"], "final_state": {k: v for k, v in result["final_state"].items() if not isinstance(v, list) or len(v) < 5},
            }, default=str) + "\n")
        log.info("  Run %d done in %.1fs | answers=%s", i, result["elapsed_seconds"], result["answers"])

    return results
