#!/usr/bin/env bash
# One-command data refresh. Rebuilds the corpus locally, pushes it, reindexes
# search, rebuilds the buyer artifact, and emails saved-query alerts.
#
# Run on the host that holds the pipeline checkout (the downloads/ + texts/
# caches). Cron it, or use the systemd timer in this directory.
#
#   SERVER=ubuntu@deathlessons.org ./server/commercial/deploy/refresh.sh
set -euo pipefail

SERVER="${SERVER:-ubuntu@deathlessons.org}"
SEARCH_DIR="${SEARCH_DIR:-/home/ubuntu/search}"
APP_DIR="${APP_DIR:-/home/ubuntu/commercial}"

# pipeline dir (notebooks/) is three levels up from this script
PIPELINE_DIR="${PIPELINE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
cd "$PIPELINE_DIR"

echo "==> [1/4] Rebuild corpus (make update)"
make update

echo "==> [2/4] Push data.json -> $SEARCH_DIR"
rsync -av --rsync-path="sudo rsync" data.json "$SERVER:$SEARCH_DIR/"

echo "==> [3/4] Reindex search + rebuild buyer artifact"
ssh "$SERVER" "set -euo pipefail
  sudo systemctl restart tantiivy.service
  cd '$APP_DIR'
  .venv/bin/python build_dataset_artifact.py '$SEARCH_DIR/data.json' data/deathlessons-corpus.jsonl.gz"

echo "==> [4/4] Email saved-query alerts"
ssh "$SERVER" "cd '$APP_DIR' && .venv/bin/python run_alerts.py"

echo "==> Refresh complete."
