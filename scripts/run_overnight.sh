#!/usr/bin/env bash
# Run forecaster + simulation + scoring end-to-end with a shared run ID.
#
# Usage: nohup ./scripts/run_overnight.sh > /tmp/iran_overnight.log 2>&1 &
#
# Outputs to results/iran_pilot/{run_id}/
set -euo pipefail

cd "$(dirname "$0")/.."
export WORLDCLONE_RUN_ID="${WORLDCLONE_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
export PYTHONPATH=.

OUT_DIR="results/iran_pilot/${WORLDCLONE_RUN_ID}"
echo "=== WorldClone overnight run ==="
echo "RUN_ID=${WORLDCLONE_RUN_ID}"
echo "OUT_DIR=${OUT_DIR}"
echo "STARTED=$(date -u -Iseconds)"
mkdir -p "${OUT_DIR}"

echo
echo "=== STAGE 1/3: Forecaster ==="
START_FORECASTER=$(date +%s)
python3 scripts/run_forecaster_iran.py 2>&1 | tee -a "${OUT_DIR}/forecaster_stdout.log"
END_FORECASTER=$(date +%s)
echo "Forecaster wall-clock: $((END_FORECASTER - START_FORECASTER))s"

echo
echo "=== STAGE 2/3: Simulation (Monte Carlo, N=15, n_steps=10) ==="
# Smoke test showed ~200s/step. n_steps=10 × 200s = 33min/run × N=15 = ~8.5 hours.
# n_steps=10 covers narrative dates Mar 28 + 30 days = Apr 27, well past all resolutions (latest is Apr 13).
START_SIM=$(date +%s)
python3 scripts/run_simulation_iran.py --n-runs 15 --n-steps 10 2>&1 | tee -a "${OUT_DIR}/simulation_stdout.log"
END_SIM=$(date +%s)
echo "Simulation wall-clock: $((END_SIM - START_SIM))s"

echo
echo "=== STAGE 3/3: Scoring & report ==="
python3 scripts/score_iran.py --run-dir "${OUT_DIR}" 2>&1 | tee -a "${OUT_DIR}/score_stdout.log"

echo
echo "=== ALL DONE ==="
echo "FINISHED=$(date -u -Iseconds)"
echo "Report: ${OUT_DIR}/report.md"
