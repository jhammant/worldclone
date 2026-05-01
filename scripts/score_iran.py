"""Score forecaster + simulation against community baselines on the Iran cluster.

Inputs:
  - results/iran_pilot/{ts}/forecasts.jsonl          (forecaster output)
  - results/iran_pilot/{ts}/simulation/aggregate.json (simulation Monte Carlo)
  - data/iran_cluster.json                            (ground truth + close prob)
  - data/iran_bet_history.json                        (time-avg community prob)

Output: results/iran_pilot/{ts}/report.md + scores.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worldclone.common.manifold import load_iran_cluster
from worldclone.scoring.brier import bootstrap_brier_ci, brier_one, log_loss_one


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True, help="results/iran_pilot/{timestamp}/")
    return p.parse_args()


def _scoreset(name: str, predictions: dict[str, float], questions: list, outcomes: dict[str, int]):
    """Compute per-question + mean Brier + log-loss for a method."""
    rows = []
    probs = []
    outs = []
    for q in questions:
        # Prefer questionnaire_key for sim aggregate; fall back to id for forecaster
        key = q.questionnaire_key if q.questionnaire_key in predictions else q.id
        p = predictions.get(key)
        if p is None:
            rows.append({"q": q.id, "p": None, "outcome": outcomes.get(q.id), "brier": None, "log_loss": None})
            continue
        o = outcomes[q.id]
        b = brier_one(p, o)
        ll = log_loss_one(p, o)
        rows.append({"q": q.id, "p": p, "outcome": o, "brier": b, "log_loss": ll})
        probs.append(p)
        outs.append(o)
    mean_brier = sum(r["brier"] for r in rows if r["brier"] is not None) / len([r for r in rows if r["brier"] is not None]) if any(r["brier"] is not None for r in rows) else float("nan")
    mean_ll = sum(r["log_loss"] for r in rows if r["log_loss"] is not None) / len([r for r in rows if r["log_loss"] is not None]) if any(r["log_loss"] is not None for r in rows) else float("nan")
    ci_lo, ci_hi = bootstrap_brier_ci(probs, outs, n_bootstrap=2000) if probs else (float("nan"), float("nan"))
    return {
        "method": name,
        "rows": rows,
        "mean_brier": mean_brier,
        "mean_log_loss": mean_ll,
        "brier_95_ci": [ci_lo, ci_hi],
    }


def _load_forecasts(run_dir: Path) -> dict[str, float]:
    f = run_dir / "forecasts.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["question_id"]] = d["probability"]
    return out


def _load_sim(run_dir: Path) -> dict[str, float]:
    f = run_dir / "simulation" / "aggregate.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    return d["probabilities"]


def _load_bet_history() -> dict[str, dict]:
    f = Path("data/iran_bet_history.json")
    if not f.exists():
        return {}
    return {row["id"]: row for row in json.loads(f.read_text())}


def _render_report(scores: list[dict], questions, run_dir: Path) -> str:
    lines = ["# Iran Cluster Pilot — Bake-Off Report", ""]
    lines.append(f"Run: `{run_dir}`")
    lines.append("")

    # Header
    lines.append("## Summary")
    lines.append("")
    lines.append("| Method | Mean Brier (lower is better) | 95% CI | Mean log-loss |")
    lines.append("|---|---|---|---|")
    for s in scores:
        lo, hi = s["brier_95_ci"]
        lines.append(f"| {s['method']} | {s['mean_brier']:.4f} | [{lo:.3f}, {hi:.3f}] | {s['mean_log_loss']:.4f} |")
    lines.append("")

    # Per-question
    lines.append("## Per-Question Probabilities")
    lines.append("")
    header = "| Q | Resolution | " + " | ".join(s["method"] for s in scores) + " |"
    sep = "|---" * (2 + len(scores)) + "|"
    lines.append(header)
    lines.append(sep)
    for i, q in enumerate(questions):
        cells = [f"{q.question[:55]}", f"**{q.resolution}**"]
        for s in scores:
            r = s["rows"][i]
            cells.append(f"{r['p']:.3f}" if r["p"] is not None else "—")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Per-Question Brier")
    lines.append("")
    header = "| Q | " + " | ".join(s["method"] for s in scores) + " |"
    sep = "|---" * (1 + len(scores)) + "|"
    lines.append(header)
    lines.append(sep)
    for i, q in enumerate(questions):
        cells = [f"{q.question[:55]}"]
        for s in scores:
            r = s["rows"][i]
            cells.append(f"{r['brier']:.4f}" if r["brier"] is not None else "—")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Run dir not found: {run_dir}", file=sys.stderr)
        return 1

    questions = load_iran_cluster()
    outcomes = {q.id: q.resolution_binary for q in questions if q.resolution_binary is not None}

    # Load all sources
    forecaster = _load_forecasts(run_dir)
    sim = _load_sim(run_dir)
    bet_history = _load_bet_history()

    # Build prediction dicts
    naive = {q.id: 0.5 for q in questions}
    community_close = {q.id: q.resolution_probability or 0.5 for q in questions}
    community_time_avg = {q.id: bet_history.get(q.id, {}).get("community_time_avg", 0.5) for q in questions}

    # Forecaster keyed by question.id; sim keyed by questionnaire_key
    forecaster_by_qid = forecaster
    sim_by_qid = {}
    for q in questions:
        if q.questionnaire_key in sim:
            sim_by_qid[q.id] = sim[q.questionnaire_key]

    scores = [
        _scoreset("naive_50", naive, questions, outcomes),
        _scoreset("community_time_avg", community_time_avg, questions, outcomes),
        _scoreset("community_close", community_close, questions, outcomes),
    ]
    if forecaster:
        scores.append(_scoreset("forecaster (Halawi-style)", forecaster_by_qid, questions, outcomes))
    if sim:
        scores.append(_scoreset("simulation (multi-agent MC)", sim_by_qid, questions, outcomes))

    # Sort by mean Brier ascending
    scores_sorted = sorted(scores, key=lambda s: s["mean_brier"])

    report_md = _render_report(scores_sorted, questions, run_dir)
    (run_dir / "report.md").write_text(report_md)
    (run_dir / "scores.json").write_text(json.dumps(scores_sorted, indent=2, default=str))

    print(report_md)
    print(f"\nWrote: {run_dir/'report.md'} and {run_dir/'scores.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
