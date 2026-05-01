"""Score box office forecasts against actuals."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worldclone.boxoffice.schemas import Film, FilmForecast
from worldclone.scoring.boxoffice import (
    absolute_percentage_error,
    baseline_median_opening,
    ci_coverage,
    log_absolute_error,
    log_mae,
    mape,
    median_ape,
    within_pct,
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True, help="results/film_forecasts/{run_id}/")
    p.add_argument("--candidates", default="data/films/candidates.json")
    return p.parse_args()


def _load_forecasts(run_dir: Path) -> dict[str, FilmForecast]:
    f = run_dir / "forecasts.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["film_id"]] = FilmForecast(**d)
    return out


def _load_films(path: Path) -> dict[str, Film]:
    with path.open() as f:
        raw = json.load(f)
    return {fd["id"]: Film(**fd) for fd in raw["films"]}


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Run dir not found: {run_dir}", file=sys.stderr)
        return 1

    films = _load_films(Path(args.candidates))
    forecasts = _load_forecasts(run_dir)

    rows = []
    preds = []
    actuals = []
    lows = []
    highs = []
    for film_id, fc in forecasts.items():
        film = films.get(film_id)
        if film is None or film.actual_opening_weekend_usd is None:
            rows.append({"film": film_id, "actual": None, "predicted": fc.point_estimate_usd, "ape": None})
            continue
        actual = film.actual_opening_weekend_usd
        pred = fc.point_estimate_usd
        ape = absolute_percentage_error(pred, actual)
        log_ae = log_absolute_error(pred, actual) if pred > 0 else float("nan")
        in_ci = fc.ci_low_usd <= actual <= fc.ci_high_usd
        rows.append({
            "film": film.title,
            "release": film.release_date,
            "predicted": pred,
            "ci_low": fc.ci_low_usd,
            "ci_high": fc.ci_high_usd,
            "actual": actual,
            "ape": ape,
            "log_ae": log_ae,
            "in_ci": in_ci,
        })
        preds.append(pred)
        actuals.append(actual)
        lows.append(fc.ci_low_usd)
        highs.append(fc.ci_high_usd)

    # Aggregate metrics (only over scored films)
    summary = {}
    if preds:
        summary["n_scored"] = len(preds)
        summary["mape"] = mape(preds, actuals)
        summary["median_ape"] = median_ape(preds, actuals)
        summary["log_mae"] = log_mae(preds, actuals)
        summary["within_20pct"] = within_pct(preds, actuals, 0.20)
        summary["within_50pct"] = within_pct(preds, actuals, 0.50)
        summary["ci_coverage_80pct_target"] = ci_coverage(lows, highs, actuals)
        # Naive baseline: median of past actuals predicted for every film
        median_baseline = baseline_median_opening(actuals)
        summary["baseline_median_predict_all"] = median_baseline
        summary["baseline_mape"] = mape([median_baseline] * len(actuals), actuals)

    # Render report
    lines = ["# Box Office Forecaster — Report", ""]
    lines.append(f"Run: `{run_dir}`")
    lines.append("")
    if not preds:
        lines.append("**No films had `actual_opening_weekend_usd` populated — cannot score.**")
        lines.append("")
        lines.append("Predictions made (awaiting ground truth):")
        for r in rows:
            lines.append(f"  - {r['film']}: predicted ${r['predicted']:,}")
    else:
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| N films scored | {summary['n_scored']} |")
        lines.append(f"| MAPE (mean APE) | {summary['mape']*100:.1f}% |")
        lines.append(f"| Median APE | {summary['median_ape']*100:.1f}% |")
        lines.append(f"| log10 MAE | {summary['log_mae']:.3f} |")
        lines.append(f"| % within ±20% | {summary['within_20pct']*100:.0f}% |")
        lines.append(f"| % within ±50% | {summary['within_50pct']*100:.0f}% |")
        lines.append(f"| 80% CI coverage (target 80%) | {summary['ci_coverage_80pct_target']*100:.0f}% |")
        lines.append(f"| Naive baseline (median-predict-all) MAPE | {summary['baseline_mape']*100:.1f}% |")
        lines.append("")
        lines.append("## Per-Film")
        lines.append("")
        lines.append("| Film | Released | Predicted | 80% CI | Actual | APE | In CI? |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in rows:
            if r["actual"] is None:
                lines.append(f"| {r['film']} | — | ${r['predicted']:,} | — | (not yet) | — | — |")
            else:
                lines.append(
                    f"| {r['film']} | {r['release']} | "
                    f"${r['predicted']/1e6:.1f}M | "
                    f"[${r['ci_low']/1e6:.1f}M, ${r['ci_high']/1e6:.1f}M] | "
                    f"${r['actual']/1e6:.1f}M | "
                    f"{r['ape']*100:.0f}% | "
                    f"{'✓' if r['in_ci'] else '✗'} |"
                )

    report = "\n".join(lines)
    (run_dir / "report.md").write_text(report)
    (run_dir / "scores.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, default=str))

    print(report)
    print(f"\nWrote: {run_dir/'report.md'}, {run_dir/'scores.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
