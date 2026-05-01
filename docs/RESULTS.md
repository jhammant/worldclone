# Results

Headline numbers across all three domains, with pointers to the raw
artifacts that produced them. Every cell here is reproducible from the
files in this repo.

## Iran 2026 cluster — 6 questions, post-resolution

Run: [`results/iran_pilot/overnight_20260427_2305Z/`](../results/iran_pilot/overnight_20260427_2305Z/)
Cutoff: 2026-03-28 (post-Khamenei-assassination, pre-resolution for all 6)
N runs: 15

| Method | Mean Brier | 95% CI | Mean log-loss |
|---|---|---|---|
| community_close (Manifold late prices) | 0.0010 | [0.0003, 0.0021] | 0.027 |
| community_time_avg (Manifold lifetime average) | 0.1061 | [0.0499, 0.1599] | 0.363 |
| simulation (multi-agent MC) | **0.1311** | [0.0363, 0.2259] | 0.359 |
| naive_50 (always 50%) | 0.2500 | [0.2500, 0.2500] | 0.693 |
| forecaster (Halawi-style) | **0.2723** | [0.0868, 0.4578] | 0.713 |

**Reading**: late-market crowd is the gold standard (priced near
1.0 confidence on already-clear questions). The simulation cleared
naive 50%. The Halawi-style LLM forecaster did not. Both LLM methods
were beaten by the Manifold time-averaged baseline, suggesting the LLM
adds noise rather than signal on this cluster.

Per-question rows: [`scores.json`](../results/iran_pilot/overnight_20260427_2305Z/scores.json).

## Box office — 10 wide releases (2025–2026)

Run: [`results/film_forecasts/big_clean_20260429_1312Z/`](../results/film_forecasts/big_clean_20260429_1312Z/)

| Metric | Value |
|---|---|
| N films scored | 10 |
| MAPE (mean APE) | **15.9%** |
| Median APE | 13.5% |
| log10 MAE | 0.068 |
| % within ±20% of actual | 80% |
| % within ±50% of actual | 100% |
| 80% CI coverage (target 80%) | 80% — calibrated |
| Naive baseline (median-predict-all) MAPE | 101.1% |

| Film | Released | Predicted | 80% CI | Actual | APE | In CI? |
|---|---|---|---|---|---|---|
| The Super Mario Galaxy Movie | 2026-04-01 | $150.0M | [$95M, $225M] | $130.9M | 15% | ✓ |
| Project Hail Mary | 2026-03-20 | $61.0M | [$38M, $70M] | $80.0M | 24% | ✗ |
| Hoppers | 2026-03-06 | $40.5M | [$22M, $55M] | $46.0M | 12% | ✓ |
| Scream 7 | 2026-02-27 | $52.8M | [$24M, $65M] | $64.1M | 18% | ✓ |
| The Drama | 2026-04-03 | $12.2M | [$2.8M, $22M] | $14.0M | 12% | ✓ |
| Reminders of Him | 2026-04-10 | $18.2M | [$14.5M, $21.5M] | $13.0M | 40% | ✗ |
| Mickey 17 | 2025-03-07 | $18.5M | [$9M, $22M] | $19.1M | 3% | ✓ |
| A Working Man | 2025-03-28 | $15.8M | [$8M, $20M] | $14.2M | 12% | ✓ |
| Heart Eyes | 2025-02-07 | $9.8M | [$3.5M, $20M] | $8.5M | 15% | ✓ |
| Sinners | 2025-04-18 | $43.5M | [$28M, $54M] | $48.0M | 9% | ✓ |

The two misses: Project Hail Mary undershot by 24% (bot didn't fully
weight the leading-indicator stack — strong tracking + saturated
trailer views). Reminders of Him overshot by 40% (book-adaptation
romance, narrower theater count than priced).

## Sports — NBA picks to date

Run: [`results/sports_forecasts/nba_20260429_1238Z/`](../results/sports_forecasts/nba_20260429_1238Z/)

NBA Game 4s scored on 2026-04-25 / 04-27:

| Date | Matchup | P(home) | Pred margin | Actual | Hit? |
|---|---|---|---|---|---|
| 2026-04-25 | Atlanta Hawks @ New York Knicks | 0.58 | +2.5 | NYK +16 | ✓ |
| 2026-04-27 | Oklahoma City Thunder @ Phoenix Suns | 0.31 | -7.5 | OKC by 9 (away win) | ✓ |

Tonight slate (2026-04-29) — picks logged
[here](../results/sports_forecasts/tonight_20260429_1502Z/accumulator.md):

| Pick | Edge (pp) | EV | Result |
|---|---|---|---|
| Arsenal vs Atlético (UCL semi leg 1) — Arsenal ML | +8.0 | +54.4% | LOST (1-1 draw, ML mis-modelled 3-way market) |
| Houston Rockets at LA Lakers — Rockets ML | +6.4 | +12.0% | **WON** (HOU 99 LAL 93) |
| LA Kings at Colorado — Avalanche ML | +5.6 | +6.0% | LOST (Kings forced G5) |

Cumulative across both nights: **4 / 7 hit rate** (57%, Wilson 95% CI
[25%, 80%]).

## Sports — weekend May 1–3 picks (publicly logged, pre-event)

Run: [`results/sports_forecasts/weekend_2026_05_01/`](../results/sports_forecasts/weekend_2026_05_01/)

| Pick | Market | Bot prob | Vegas no-vig | Edge | EV |
|---|---|---|---|---|---|
| Montreal Canadiens (home) vs TBL, NHL G6 | -105 | 55.8% | 48.4% | +7.4 pp | +8.9% |
| Vegas Golden Knights (away) at UTA, NHL G6 | -115 | 56.7% | 51.1% | +5.6 pp | +6.0% |
| Manchester United (home) vs Liverpool, EPL | +130 | 45.5% | 41.2% | +4.3 pp | +4.6% |
| Boston Bruins (home) vs BUF, NHL G6 | -110 | 53.7% | 49.5% | +4.2 pp | +2.5% |

| Parlay | Combined decimal | Bot joint P | Vegas joint P | EV/$1 |
|---|---|---|---|---|
| 3-leg (MTL + VGK + MUN) | 8.40x | 14.4% | 10.2% | **+20.9%** |
| 4-leg (+ BOS Bruins) | 16.03x | 7.7% | 5.0% | **+23.9%** |

**Score-back**: Monday 2026-05-04. Same file gets the actuals appended
under a "Results" heading. Win or lose, the original predictions are
hash-chained and untouched.

## Reproducing

Every score in this file was produced by code in this repo:

```bash
# Iran cluster
uv run python scripts/score_iran.py --run-dir results/iran_pilot/overnight_20260427_2305Z

# Box office
uv run python scripts/score_films.py --run-dir results/film_forecasts/big_clean_20260429_1312Z

# Sports
uv run python scripts/score_sports.py --run-dir results/sports_forecasts/nba_20260429_1238Z
```

The unit tests in `tests/test_brier.py` and `tests/test_boxoffice_scoring.py`
hand-compute these metrics on small fixtures so you can sanity-check the
math against worked examples.
