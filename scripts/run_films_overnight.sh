#!/usr/bin/env bash
# Box office overnight run: forecaster + scoring on data/films/candidates.json.
#
# Usage: nohup ./scripts/run_films_overnight.sh > /tmp/films_overnight.log 2>&1 &
#
# Outputs to results/film_forecasts/{run_id}/
set -euo pipefail

cd "$(dirname "$0")/.."
export WORLDCLONE_RUN_ID="${WORLDCLONE_RUN_ID:-films_$(date -u +%Y%m%d_%H%M)Z}"
export PYTHONPATH=.

OUT_DIR="results/film_forecasts/${WORLDCLONE_RUN_ID}"
echo "=== WorldClone film overnight run ==="
echo "RUN_ID=${WORLDCLONE_RUN_ID}"
echo "OUT_DIR=${OUT_DIR}"
echo "STARTED=$(date -u -Iseconds)"
mkdir -p "${OUT_DIR}"

echo
echo "=== STAGE 1/2: Forecaster ==="
START=$(date +%s)
python3 scripts/run_film_forecaster.py 2>&1 | tee -a "${OUT_DIR}/forecaster_stdout.log"
echo "Forecaster wall-clock: $(( $(date +%s) - START ))s"

echo
echo "=== STAGE 2/2: Score ==="
python3 scripts/score_films.py --run-dir "${OUT_DIR}" 2>&1 | tee -a "${OUT_DIR}/score_stdout.log"

echo
echo "=== ALL DONE ==="
echo "FINISHED=$(date -u -Iseconds)"
echo "Report: ${OUT_DIR}/report.md"
