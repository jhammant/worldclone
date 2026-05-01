"""Run the sports game forecaster on a list of games."""
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
from worldclone.sports.pipeline import forecast_game
from worldclone.sports.schemas import Game


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--games", default="data/sports/games.json")
    p.add_argument("--n-games", type=int, default=0)
    p.add_argument("--as-of-date", default=None,
                   help="Forecast cutoff (default: 1 day before game_date)")
    p.add_argument("--out-dir", default="results/sports_forecasts")
    return p.parse_args()


def default_as_of_date(game_date_iso: str) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(game_date_iso) - timedelta(days=1)).isoformat()


async def main_async() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    llm.init()

    with Path(args.games).open() as f:
        raw = json.load(f)
    games = [Game(**g) for g in raw["games"]]
    if args.n_games > 0:
        games = games[: args.n_games]

    run_id = os.environ.get("WORLDCLONE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Forecasting {len(games)} game(s); out_dir={out_dir}")

    t_start = time.time()
    for game in games:
        as_of = args.as_of_date or default_as_of_date(game.game_date)
        try:
            fc = await forecast_game(game, as_of_date=as_of)
            with (out_dir / "forecasts.jsonl").open("a") as fp:
                fp.write(fc.model_dump_json() + "\n")
            print(f"  [{game.id}] P(home)={fc.p_home_win:.2f}  "
                  f"margin={fc.predicted_margin_home:+.1f}  "
                  f"total={fc.predicted_total or 0:.1f}  "
                  f"in {fc.elapsed_seconds:.1f}s")
        except Exception as e:
            print(f"  [{game.id}] FAILED: {e}", file=sys.stderr)
            logging.exception("forecast failed")

    print(f"\nTotal wall-clock: {(time.time()-t_start)/60:.1f} min")
    print(f"LLM accountant: {llm.accountant().summary()}")
    print(f"Results: {out_dir}/forecasts.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
