"""Run the Halawi-style forecaster on the 6 Iran-cluster questions."""
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
from worldclone.forecaster.pipeline import forecast_question


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n-questions", type=int, default=0, help="If >0, only run on the first N questions")
    p.add_argument("--ensemble-k", type=int, default=5, help="(reserved; ensemble fixed in prompts.py for now)")
    p.add_argument("--as-of-date", default="2026-03-28", help="Pre-resolution cutoff for evidence")
    p.add_argument("--out-dir", default="results/iran_pilot")
    return p.parse_args()


async def main_async() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    args = parse_args()

    # Load environment
    env_path = Path(".env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv  # type: ignore[import-not-found]
            load_dotenv(env_path)
        except ImportError:
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    llm.init()
    questions = load_iran_cluster()
    if args.n_questions > 0:
        questions = questions[: args.n_questions]
    print(f"Forecasting {len(questions)} questions; as_of_date={args.as_of_date}")

    run_id = os.environ.get("WORLDCLONE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  out_dir={out_dir}")

    results = []
    t_start = time.time()
    for q in questions:
        try:
            r = await forecast_question(q, as_of_date=args.as_of_date)
            results.append(r)
            # Append to JSONL incrementally so a crash doesn't lose progress
            with (out_dir / "forecasts.jsonl").open("a") as f:
                f.write(r.model_dump_json() + "\n")
            print(f"  [{q.id}] P(YES)={r.probability:.3f} in {r.elapsed_seconds:.1f}s "
                  f"(individuals={[round(p,2) for p in r.ensemble_probabilities]})")
        except Exception as e:
            print(f"  [{q.id}] FAILED: {e}", file=sys.stderr)
            logging.exception("forecast failed")

    print(f"\nTotal wall-clock: {time.time()-t_start:.1f}s")
    print(f"LLM accountant summary: {llm.accountant().summary()}")
    print(f"Results: {out_dir}/forecasts.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
