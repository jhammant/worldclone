"""Run the box office forecaster on a list of films."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from worldclone.boxoffice.pipeline import forecast_film
from worldclone.boxoffice.schemas import Film
from worldclone.common import llm


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", default="data/films/candidates.json")
    p.add_argument("--n-films", type=int, default=0, help="If >0, only the first N films from the list")
    p.add_argument("--as-of-date", default=None, help="Override forecast cutoff (default: 4 days before release)")
    p.add_argument("--out-dir", default="results/film_forecasts")
    return p.parse_args()


def default_as_of_date(release_date_iso: str) -> str:
    """Forecast cutoff convention: 4 days before release (e.g. Mon for Fri opening)."""
    rd = date.fromisoformat(release_date_iso)
    return (rd - timedelta(days=4)).isoformat()


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

    with Path(args.candidates).open() as f:
        raw = json.load(f)
    films = [Film(**fd) for fd in raw["films"]]
    if args.n_films > 0:
        films = films[: args.n_films]

    run_id = os.environ.get("WORLDCLONE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Forecasting {len(films)} films; out_dir={out_dir}")

    t_start = time.time()
    forecasts = []
    for film in films:
        as_of = args.as_of_date or default_as_of_date(film.release_date)
        try:
            f = await forecast_film(film, as_of_date=as_of)
            forecasts.append(f)
            with (out_dir / "forecasts.jsonl").open("a") as fp:
                fp.write(f.model_dump_json() + "\n")
            print(f"  [{film.id}] point=${f.point_estimate_usd:,} ({f.point_estimate_usd/1e6:.1f}M) "
                  f"80% CI=[${f.ci_low_usd/1e6:.1f}M, ${f.ci_high_usd/1e6:.1f}M] "
                  f"in {f.elapsed_seconds:.1f}s")
        except Exception as e:
            print(f"  [{film.id}] FAILED: {e}", file=sys.stderr)
            logging.exception("forecast failed")

    print(f"\nTotal wall-clock: {time.time()-t_start:.1f}s")
    print(f"LLM accountant: {llm.accountant().summary()}")
    print(f"Results: {out_dir}/forecasts.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
