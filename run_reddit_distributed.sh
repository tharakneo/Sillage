#!/usr/bin/env bash
# Distributed Reddit scrape for all SKUs in src/sku_config.py.
# Splits the date range into 6-month chunks run in parallel, then merges.
#
# Usage:
#   ./run_reddit_distributed.sh START_YEAR END_YEAR
#   ./run_reddit_distributed.sh 2023 2025      # scrapes Jan 2023 – Dec 2025
#
# Each chunk writes data/raw/_partial/{tag}.{csv,log}.
# Tail progress with: tail -f data/raw/_partial/*.log

set -euo pipefail
cd "$(dirname "$0")"

START_YEAR="${1:?usage: ./run_reddit_distributed.sh START_YEAR END_YEAR}"
END_YEAR="${2:?usage: ./run_reddit_distributed.sh START_YEAR END_YEAR}"

PY=./venv/bin/python
mkdir -p data/raw/_partial

echo "Launching parallel half-year chunks ($START_YEAR–$END_YEAR)..."

pids=()
for year in $(seq "$START_YEAR" "$END_YEAR"); do
  $PY src/ingest_reddit.py --start "$year-01-01" --end "$year-06-30" \
      --tag "h1_$year" > "data/raw/_partial/h1_$year.log" 2>&1 &
  pids+=($!)
  $PY src/ingest_reddit.py --start "$year-07-01" --end "$year-12-31" \
      --tag "h2_$year" > "data/raw/_partial/h2_$year.log" 2>&1 &
  pids+=($!)
done

echo "PIDs: ${pids[*]}"
echo "Tail progress with: tail -f data/raw/_partial/*.log"
wait "${pids[@]}"

echo ""
echo "All chunks done. Merging..."
$PY src/merge_reddit.py
echo "Complete."
