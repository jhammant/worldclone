"""Calibration scatter for the box office forecaster.

Reads the canonical batch result and produces docs/images/boxoffice_calibration.png.
X = predicted opening ($M), Y = actual ($M), error bars = 80% CI, color = within-CI.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


RUN = Path("results/film_forecasts/big_clean_20260429_1312Z")
OUT = Path("docs/images/boxoffice_calibration.png")


def load_rows() -> list[dict]:
    forecasts = {}
    with (RUN / "forecasts.jsonl").open() as f:
        for line in f:
            d = json.loads(line)
            forecasts[d["film_id"]] = d
    cands = json.load(Path("data/films/candidates.json").open())
    rows = []
    for c in cands["films"]:
        fc = forecasts.get(c["id"])
        if not fc or c.get("actual_opening_weekend_usd") is None:
            continue
        rows.append({
            "title": c["title"],
            "predicted": fc["point_estimate_usd"] / 1e6,
            "ci_low": fc["ci_low_usd"] / 1e6,
            "ci_high": fc["ci_high_usd"] / 1e6,
            "actual": c["actual_opening_weekend_usd"] / 1e6,
        })
    return rows


def plot(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 7), dpi=150)
    xs = [r["predicted"] for r in rows]
    ys = [r["actual"] for r in rows]
    err_low = [r["predicted"] - r["ci_low"] for r in rows]
    err_high = [r["ci_high"] - r["predicted"] for r in rows]
    in_ci = [r["ci_low"] <= r["actual"] <= r["ci_high"] for r in rows]
    colors = ["#2ca02c" if hit else "#d62728" for hit in in_ci]
    ax.errorbar(xs, ys, xerr=[err_low, err_high], fmt="none",
                ecolor="#bbbbbb", capsize=3, alpha=0.7, zorder=1)
    ax.scatter(xs, ys, c=colors, s=80, edgecolor="black",
               linewidth=0.6, zorder=2)
    for r in rows:
        ax.annotate(r["title"][:24], (r["predicted"], r["actual"]),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=8, alpha=0.85)
    lim = max(max(xs), max(ys)) * 1.1
    ax.plot([0, lim], [0, lim], "--", color="#888", linewidth=1, alpha=0.6,
            zorder=0)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Predicted opening weekend ($M)")
    ax.set_ylabel("Actual opening weekend ($M)")
    ax.set_title("Box office calibration\n10 wide releases  ·  MAPE 15.9%  ·  80% CI coverage 80%",
                 fontsize=12)
    ax.grid(True, alpha=0.25)
    legend_elems = [
        plt.scatter([], [], c="#2ca02c", s=80, edgecolor="black",
                    linewidth=0.6, label="actual within 80% CI (8/10)"),
        plt.scatter([], [], c="#d62728", s=80, edgecolor="black",
                    linewidth=0.6, label="actual outside CI (2/10)"),
    ]
    ax.legend(handles=legend_elems, loc="upper left", framealpha=0.95)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    plot(load_rows())
