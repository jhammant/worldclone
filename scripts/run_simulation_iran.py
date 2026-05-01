"""Run the Iran 2026 multi-agent Monte Carlo simulation."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from worldclone.common import llm
from worldclone.common.manifold import load_iran_cluster
from worldclone.simulation.extract import aggregate
from worldclone.simulation.loop import run_simulation
from worldclone.simulation.scenario import Scenario


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n-runs", type=int, default=15)
    p.add_argument("--n-steps", type=int, default=12)
    p.add_argument("--days-per-step", type=int, default=3)
    p.add_argument("--base-seed", type=int, default=42)
    p.add_argument("--out-dir", default="results/iran_pilot")
    p.add_argument("--max-runtime-hours", type=float, default=10.0)
    return p.parse_args()


async def main_async() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    llm.init(max_runtime_hours=args.max_runtime_hours)
    scenario = Scenario.load()
    questions = load_iran_cluster()
    print(f"Simulation: n_runs={args.n_runs} n_steps={args.n_steps} days_per_step={args.days_per_step}")
    print(f"  scenario: {len(scenario.actors)} actors, {len(scenario.facts)} facts up to {scenario.cutoff_date}")
    print(f"  questions: {len(questions)}")

    run_id = os.environ.get("WORLDCLONE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / run_id / "simulation"
    print(f"  out_dir={out_dir}")

    t_start = time.time()
    runs = await run_simulation(
        scenario=scenario,
        questions=questions,
        n_runs=args.n_runs,
        n_steps=args.n_steps,
        days_per_step=args.days_per_step,
        out_dir=out_dir,
        base_seed=args.base_seed,
    )
    elapsed = time.time() - t_start

    agg = aggregate(runs, questions, model_name=os.environ.get("WORLDCLONE_LLM_MODEL", ""))
    with (out_dir / "aggregate.json").open("w") as f:
        json.dump(agg.model_dump(), f, indent=2, default=str)

    print(f"\n=== Results ===")
    print(f"Total wall-clock: {elapsed/60:.1f} min")
    for q in questions:
        k = q.questionnaire_key
        p = agg.probabilities[k]
        lo, hi = agg.wilson_ci[k]
        actual = q.resolution
        print(f"  {q.id} [{actual:>3}] P(YES)={p:.3f} 95%CI=[{lo:.2f},{hi:.2f}] | {q.question[:60]}")
    print(f"\nLLM accountant summary: {llm.accountant().summary()}")
    print(f"Results: {out_dir}/aggregate.json + runs/run_*.json")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
