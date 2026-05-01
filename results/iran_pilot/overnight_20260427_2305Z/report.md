# Iran Cluster Pilot — Bake-Off Report

Run: `results/iran_pilot/overnight_20260427_2305Z`

## Summary

| Method | Mean Brier (lower is better) | 95% CI | Mean log-loss |
|---|---|---|---|
| community_close | 0.0010 | [0.000, 0.002] | 0.0268 |
| community_time_avg | 0.1061 | [0.050, 0.160] | 0.3633 |
| simulation (multi-agent MC) | 0.1311 | [0.036, 0.226] | 0.3588 |
| naive_50 | 0.2500 | [0.250, 0.250] | 0.6931 |
| forecaster (Halawi-style) | 0.2723 | [0.087, 0.458] | 0.7131 |

## Per-Question Probabilities

| Q | Resolution | community_close | community_time_avg | simulation (multi-agent MC) | naive_50 | forecaster (Halawi-style) |
|---|---|---|---|---|---|---|
| Will the US put boots on the ground in Iran in 2026? | **YES** | 0.983 | 0.532 | 0.467 | 0.500 | 0.230 |
| Will Iran shoot down a US military plane/helicopter by  | **NO** | 0.028 | 0.352 | 0.000 | 0.500 | 0.250 |
| Will President Trump put "boots on the ground" in Iran  | **YES** | 0.984 | 0.707 | 0.467 | 0.500 | 0.270 |
| Will Iran kill atleast 5 more American soldiers by end  | **NO** | 0.060 | 0.395 | 0.000 | 0.500 | 0.110 |
| Trump will nuke Iran by 8pm EST 10 April 2026 | **NO** | 0.001 | 0.007 | 0.000 | 0.500 | 0.022 |
| Will Trump attack Iran's infrastructure before April 13 | **NO** | 0.036 | 0.228 | 0.467 | 0.500 | 0.658 |

## Per-Question Brier

| Q | community_close | community_time_avg | simulation (multi-agent MC) | naive_50 | forecaster (Halawi-style) |
|---|---|---|---|---|---|
| Will the US put boots on the ground in Iran in 2026? | 0.0003 | 0.2189 | 0.2844 | 0.2500 | 0.5929 |
| Will Iran shoot down a US military plane/helicopter by  | 0.0008 | 0.1236 | 0.0000 | 0.2500 | 0.0625 |
| Will President Trump put "boots on the ground" in Iran  | 0.0003 | 0.0857 | 0.2844 | 0.2500 | 0.5329 |
| Will Iran kill atleast 5 more American soldiers by end  | 0.0036 | 0.1561 | 0.0000 | 0.2500 | 0.0121 |
| Trump will nuke Iran by 8pm EST 10 April 2026 | 0.0000 | 0.0001 | 0.0000 | 0.2500 | 0.0005 |
| Will Trump attack Iran's infrastructure before April 13 | 0.0013 | 0.0521 | 0.2178 | 0.2500 | 0.4330 |
