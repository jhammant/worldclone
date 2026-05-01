# Box Office Forecaster — Report

Run: `results/film_forecasts/big_clean_20260429_1312Z`

## Summary

| Metric | Value |
|---|---|
| N films scored | 10 |
| MAPE (mean APE) | 15.9% |
| Median APE | 13.5% |
| log10 MAE | 0.068 |
| % within ±20% | 80% |
| % within ±50% | 100% |
| 80% CI coverage (target 80%) | 80% |
| Naive baseline (median-predict-all) MAPE | 101.1% |

## Per-Film

| Film | Released | Predicted | 80% CI | Actual | APE | In CI? |
|---|---|---|---|---|---|---|
| The Super Mario Galaxy Movie | 2026-04-01 | $150.0M | [$95.0M, $225.0M] | $130.9M | 15% | ✓ |
| Project Hail Mary (film) | 2026-03-20 | $61.0M | [$38.0M, $70.0M] | $80.0M | 24% | ✗ |
| Hoppers (film) | 2026-03-06 | $40.5M | [$22.0M, $55.0M] | $46.0M | 12% | ✓ |
| Scream 7 | 2026-02-27 | $52.8M | [$24.0M, $65.0M] | $64.1M | 18% | ✓ |
| The Drama (film) | 2026-04-03 | $12.2M | [$2.8M, $22.0M] | $14.0M | 12% | ✓ |
| Reminders of Him (film) | 2026-04-10 | $18.2M | [$14.5M, $21.5M] | $13.0M | 40% | ✗ |
| Mickey 17 | 2025-03-07 | $18.5M | [$9.0M, $22.0M] | $19.1M | 3% | ✓ |
| A Working Man (film) | 2025-03-28 | $15.8M | [$8.0M, $20.0M] | $14.2M | 12% | ✓ |
| Heart Eyes (film) | 2025-02-07 | $9.8M | [$3.5M, $20.0M] | $8.5M | 15% | ✓ |
| Sinners (2025 film) | 2025-04-18 | $43.5M | [$28.0M, $54.0M] | $48.0M | 9% | ✓ |