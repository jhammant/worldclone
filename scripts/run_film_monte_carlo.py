"""End-to-end: forecast opening weekend → Monte Carlo first-week distribution.

For each film in candidates.json:
  1. Run the 5-variant Halawi-style ensemble forecaster (with Exa retrieval if key set)
  2. Feed the (point, low, high) into the Monte Carlo simulator
  3. Save FilmForecast + FirstWeekForecast + a markdown report per film

Reuses scripts/run_film_forecaster.py outputs if --reuse-forecasts is set.
"""
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

from worldclone.boxoffice.monte_carlo import monte_carlo_first_week, render_first_week_text
from worldclone.boxoffice.pipeline import forecast_film
from worldclone.boxoffice.schemas import Film, FilmForecast
from worldclone.common import llm


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", default="data/films/candidates.json")
    p.add_argument("--n-films", type=int, default=0)
    p.add_argument("--n-samples", type=int, default=5000, help="Monte Carlo sample count")
    p.add_argument("--as-of-date", default=None)
    p.add_argument("--out-dir", default="results/film_forecasts")
    p.add_argument("--reuse-forecasts", action="store_true",
                   help="If a forecasts.jsonl already exists in out-dir, skip the LLM forecaster step")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def default_as_of_date(release_date_iso: str) -> str:
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
    print(f"Forecasting + MC for {len(films)} film(s); out_dir={out_dir}")

    # Optionally reuse prior forecasts
    existing_forecasts: dict[str, FilmForecast] = {}
    if args.reuse_forecasts:
        f = out_dir / "forecasts.jsonl"
        if f.exists():
            for line in f.read_text().splitlines():
                if line.strip():
                    d = json.loads(line)
                    existing_forecasts[d["film_id"]] = FilmForecast(**d)
            print(f"  reusing {len(existing_forecasts)} prior forecast(s)")

    t_start = time.time()
    reports = []
    for film in films:
        as_of = args.as_of_date or default_as_of_date(film.release_date)
        try:
            if film.id in existing_forecasts:
                fc = existing_forecasts[film.id]
                print(f"  [{film.id}] reusing forecast: ${fc.point_estimate_usd/1e6:.1f}M point")
            else:
                fc = await forecast_film(film, as_of_date=as_of)
                with (out_dir / "forecasts.jsonl").open("a") as fp:
                    fp.write(fc.model_dump_json() + "\n")
                print(f"  [{film.id}] OW forecast: ${fc.point_estimate_usd/1e6:.1f}M "
                      f"(80% CI [${fc.ci_low_usd/1e6:.1f}M, ${fc.ci_high_usd/1e6:.1f}M]) in {fc.elapsed_seconds:.1f}s")

            fw = monte_carlo_first_week(film, fc, n_samples=args.n_samples, seed=args.seed)
            with (out_dir / "first_week.jsonl").open("a") as fp:
                fp.write(fw.model_dump_json() + "\n")
            print(f"  [{film.id}] MC first-week median: ${fw.first_week_median_usd/1e6:.1f}M "
                  f"(P10–P90: ${fw.first_week_p10_usd/1e6:.1f}M–${fw.first_week_p90_usd/1e6:.1f}M)")

            md = render_first_week_text(film, fw)
            (out_dir / f"{film.id}_first_week.md").write_text(md)
            reports.append((film, fc, fw))
        except Exception as e:
            print(f"  [{film.id}] FAILED: {e}", file=sys.stderr)
            logging.exception("MC failed")

    # Combined report
    md_lines = [f"# First-week box office Monte Carlo — {run_id}", ""]
    md_lines.append(f"Wall-clock: {(time.time()-t_start)/60:.1f} min  |  Samples per film: {args.n_samples:,}")
    md_lines.append("")
    md_lines.append("## Summary")
    md_lines.append("")
    md_lines.append("| Film | OW point | OW 80% CI | First-week P10 | Median | P90 | Actual OW |")
    md_lines.append("|---|---|---|---|---|---|---|")
    for film, fc, fw in reports:
        actual_ow = f"${film.actual_opening_weekend_usd/1e6:.1f}M" if film.actual_opening_weekend_usd else "—"
        md_lines.append(
            f"| {film.title} | ${fc.point_estimate_usd/1e6:.1f}M | "
            f"[${fc.ci_low_usd/1e6:.1f}M, ${fc.ci_high_usd/1e6:.1f}M] | "
            f"${fw.first_week_p10_usd/1e6:.1f}M | "
            f"**${fw.first_week_median_usd/1e6:.1f}M** | "
            f"${fw.first_week_p90_usd/1e6:.1f}M | "
            f"{actual_ow} |"
        )
    for film, fc, fw in reports:
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        md_lines.append(render_first_week_text(film, fw))
    (out_dir / "report.md").write_text("\n".join(md_lines))

    print(f"\nTotal wall-clock: {(time.time()-t_start)/60:.1f} min")
    print(f"LLM accountant: {llm.accountant().summary()}")
    print(f"Report: {out_dir/'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
