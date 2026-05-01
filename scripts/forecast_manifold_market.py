"""Forecast any single Manifold market by ID or URL.

Generalizes the Iran-cluster pipeline to work on arbitrary Manifold markets.
Reuses the existing forecaster.pipeline (5-variant Halawi ensemble + Exa retrieval).

Usage:
    uv run python scripts/forecast_manifold_market.py --market-id 56EZq5c6QS
    uv run python scripts/forecast_manifold_market.py --url https://manifold.markets/.../slug
    uv run python scripts/forecast_manifold_market.py --slug will-the-us-put-boots-on-the-ground

Optionally save to results/manifold_forecasts/{run_id}/forecasts.jsonl for batch tracking.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from worldclone.common import llm
from worldclone.common.io import ManifoldQuestion
from worldclone.forecaster.pipeline import forecast_question


def parse_args():
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--market-id", help="Manifold market id (short string, e.g. 56EZq5c6QS)")
    src.add_argument("--slug", help="Manifold slug (e.g. will-the-us-put-boots-on-the-ground)")
    src.add_argument("--url", help="Manifold market URL")
    src.add_argument("--ids-file", help="JSON file containing a list of market_id strings to batch")
    p.add_argument("--criteria",
                   help="Optional resolution criteria override. If omitted, uses Manifold market description.")
    p.add_argument("--as-of-date", default=None,
                   help="Forecast cutoff (default: 1 day before close, or today if market is open)")
    p.add_argument("--out-dir", default="results/manifold_forecasts")
    p.add_argument("--no-save", action="store_true",
                   help="Print forecast but do not write to disk")
    return p.parse_args()


def fetch_market_by_id(market_id: str) -> dict:
    url = f"https://api.manifold.markets/v0/market/{urllib.parse.quote(market_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_market_by_slug(slug: str) -> dict:
    url = f"https://api.manifold.markets/v0/slug/{urllib.parse.quote(slug)}"
    req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def market_to_question(market: dict, criteria_override: str | None = None) -> ManifoldQuestion:
    """Convert a Manifold market dict to our ManifoldQuestion schema.

    Uses the market's `textDescription` (or `description`) as resolution criteria
    unless overridden.
    """
    desc = market.get("textDescription") or market.get("description") or ""
    if isinstance(desc, dict):
        # Sometimes Manifold's description is a Tiptap doc; flatten to text
        def flatten(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                return "".join(flatten(c) for c in node.get("content", []))
            return ""
        desc = flatten(desc)
    return ManifoldQuestion(
        id=market["id"],
        question=market["question"],
        url=market.get("url", f"https://manifold.markets/{market.get('creatorUsername','')}/{market.get('slug','')}"),
        resolution=market.get("resolution"),
        resolution_probability=market.get("resolutionProbability") or market.get("probability"),
        resolution_time_ms=market.get("resolutionTime"),
        close_time_ms=market.get("closeTime"),
        create_time_ms=market.get("createdTime"),
        volume=market.get("volume", 0.0),
        unique_bettors=market.get("uniqueBettorCount", 0),
        resolution_criteria=criteria_override or desc[:2000],
        questionnaire_key=re.sub(r"[^a-z0-9]+", "_", market["question"].lower())[:60],
        questionnaire_prompt=market["question"],
    )


def default_as_of_date(market: dict) -> str:
    """Forecast cutoff: today (for open markets) or 1 day before close (resolved)."""
    close = market.get("closeTime")
    if close:
        close_d = datetime.fromtimestamp(close / 1000, tz=timezone.utc).date()
        cutoff = close_d - timedelta(days=1)
        # If close was in the future, use today instead
        today = datetime.now(timezone.utc).date()
        if cutoff > today:
            cutoff = today
        return cutoff.isoformat()
    return datetime.now(timezone.utc).date().isoformat()


async def forecast_one(market_id: str, *, criteria_override: str | None, as_of_date_arg: str | None,
                       out_dir: Path | None) -> dict:
    market = fetch_market_by_id(market_id)
    q = market_to_question(market, criteria_override)
    as_of = as_of_date_arg or default_as_of_date(market)

    logging.info("Forecasting %s — %s (cutoff %s)", q.id, q.question[:80], as_of)

    res = await forecast_question(q, as_of_date=as_of)

    out = {
        "question_id": q.id,
        "question": q.question,
        "url": q.url,
        "is_resolved": q.resolution in ("YES", "NO"),
        "actual_resolution": q.resolution,
        "community_close_prob": q.resolution_probability,
        "forecast_probability": res.probability,
        "ensemble": res.ensemble_probabilities,
        "as_of_date": as_of,
        "n_articles": res.n_articles_used,
        "elapsed_seconds": res.elapsed_seconds,
        "model": res.model,
        "reasoning": res.reasoning,
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "forecasts.jsonl").open("a") as f:
            f.write(json.dumps(out) + "\n")

    print(f"\n=== {q.question} ===")
    print(f"  URL: {q.url}")
    print(f"  Forecast P(YES): {res.probability:.3f}  (ensemble {[round(p,2) for p in res.ensemble_probabilities]})")
    if q.resolution_probability is not None:
        print(f"  Community @ close: {q.resolution_probability:.3f}")
    if q.resolution:
        print(f"  Actual: {q.resolution}")
    print(f"  Articles used: {res.n_articles_used}  ({res.elapsed_seconds:.1f}s)")
    return out


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

    # Resolve market IDs
    ids: list[str] = []
    if args.ids_file:
        with Path(args.ids_file).open() as f:
            ids = json.load(f)
    elif args.market_id:
        ids = [args.market_id]
    elif args.slug:
        m = fetch_market_by_slug(args.slug)
        ids = [m["id"]]
    elif args.url:
        # parse last path segment as slug
        slug = args.url.rstrip("/").split("/")[-1]
        m = fetch_market_by_slug(slug)
        ids = [m["id"]]

    run_id = os.environ.get("WORLDCLONE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = None if args.no_save else Path(args.out_dir) / run_id
    if out_dir:
        print(f"out_dir = {out_dir}")

    t_start = time.time()
    for mid in ids:
        try:
            await forecast_one(
                mid,
                criteria_override=args.criteria,
                as_of_date_arg=args.as_of_date,
                out_dir=out_dir,
            )
        except Exception as e:
            print(f"  [{mid}] FAILED: {e}", file=sys.stderr)
            logging.exception("forecast failed")
    print(f"\nTotal wall-clock: {(time.time()-t_start)/60:.1f} min")
    print(f"LLM accountant: {llm.accountant().summary()}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
