#!/usr/bin/env bash
# One-command deploy of deathlessons.org: static site, search data, and the
# commercial app. Run from a machine with SSH access to the server. Idempotent
# — safe to re-run after any code change.
#
#   SERVER=ubuntu@deathlessons.org ./server/commercial/deploy/deploy.sh
#
# First run only: afterwards, edit /home/ubuntu/commercial/.env on the server
# with your real secrets, re-run this, and obtain TLS:
#   ssh $SERVER 'sudo certbot --nginx -d app.deathlessons.org'
set -euo pipefail

SERVER="${SERVER:-ubuntu@deathlessons.org}"
WEB_ROOT="${WEB_ROOT:-/var/www/html}"
SEARCH_DIR="${SEARCH_DIR:-/home/ubuntu/search}"
APP_DIR="${APP_DIR:-/home/ubuntu/commercial}"

# repo root (notebooks/) is three levels up from this script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

RSYNC=(rsync -av --rsync-path="sudo rsync")

echo "==> [1/4] Static site -> $WEB_ROOT"
# Stamp today's date into the homepage "last updated" line so it never drifts.
stamp="$(date +'%-d %B %Y')"
tmp_index="$(mktemp)"
sed "s/Dataset last updated [^(]*(/Dataset last updated ${stamp} (/" server/app/index.html > "$tmp_index"
chmod 644 "$tmp_index"   # mktemp makes 0600; rsync -a would copy that and nginx 403s
"${RSYNC[@]}" "$tmp_index" "$SERVER:$WEB_ROOT/index.html"
"${RSYNC[@]}" server/app/why.html server/app/style.css "$SERVER:$WEB_ROOT/"
rm -f "$tmp_index"

echo "==> [2/4] Search data -> $SEARCH_DIR"
if [ -f data.json ]; then
  "${RSYNC[@]}" data.json "$SERVER:$SEARCH_DIR/"
else
  echo "    (no data.json here; skipping — run 'make update' first if you meant to)"
fi

echo "==> [3/4] Commercial app -> $APP_DIR"
"${RSYNC[@]}" --delete \
  --exclude '.venv' --exclude 'data' --exclude '.env' --exclude '__pycache__' \
  server/commercial/ "$SERVER:$APP_DIR/"

echo "==> [4/4] Remote setup + restart"
ssh "$SERVER" "APP_DIR='$APP_DIR' SEARCH_DIR='$SEARCH_DIR' bash -s" <<'REMOTE'
set -euo pipefail
cd "$APP_DIR"

# (re)create the venv. A failed earlier run can leave a .venv with no pip
# (e.g. python3-venv/ensurepip missing), so key off pip, not the directory.
if [ ! -x .venv/bin/pip ]; then
  rm -rf .venv
  if ! python3 -m venv .venv; then
    echo "!! venv creation failed. Install the venv package on the server, e.g.:"
    echo "!!   sudo apt-get update && sudo apt-get install -y python3-venv"
    echo "!! then re-run deploy.sh."
    exit 1
  fi
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
mkdir -p data

# First run: seed .env so the service can start; you must then fill it in.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! Created $APP_DIR/.env from the example — EDIT IT with real secrets,"
  echo "!! then re-run deploy.sh (or: sudo systemctl restart commercial)."
fi

# Rebuild the buyer artifact from the freshly-pushed data.json (if present).
if [ -f "$SEARCH_DIR/data.json" ]; then
  .venv/bin/python build_dataset_artifact.py "$SEARCH_DIR/data.json" \
      data/deathlessons-corpus.jsonl.gz || true
fi

# systemd service
if [ ! -f /etc/systemd/system/commercial.service ]; then
  sudo cp deploy/commercial.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable commercial
fi
sudo systemctl restart commercial

# nginx reverse proxy
if [ ! -f /etc/nginx/sites-available/commercial ]; then
  sudo cp deploy/nginx-commercial.conf /etc/nginx/sites-available/commercial
  sudo ln -sf /etc/nginx/sites-available/commercial /etc/nginx/sites-enabled/commercial
fi
sudo nginx -t && sudo systemctl reload nginx

# reindex search with the new data
sudo systemctl restart tantiivy.service
echo "remote setup complete"
REMOTE

echo "==> Deploy complete."
