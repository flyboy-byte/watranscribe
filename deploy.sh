#!/usr/bin/env bash
# Deploy latest code to the VPS and restart the transcribe.service user unit.
# Run from local machine: ./deploy.sh
#
# Mirrors the same pattern used by the other flyboybyte.com projects on this
# VPS (see ~/budget/deploy.sh there) — push to GitHub, then pull+restart
# remotely rather than rsync'ing local state.
set -euo pipefail

# VPS host lives in .env as VPS_HOST=user@host — not committed.
VPS=$(grep -E '^VPS_HOST=' .env | cut -d= -f2-)
[ -n "$VPS" ] || { echo "VPS_HOST not set in .env (e.g. VPS_HOST=ubuntu@flyboybyte.com)"; exit 1; }

echo "=== Pre-deploy checks ==="
if ! git diff-index --quiet HEAD --; then
    echo "WARNING: uncommitted local changes (not deployed — only what's pushed to GitHub)."
fi

echo "--- git push ---"
git push origin main

echo ""
echo "=== Deploying to $VPS ==="

ssh "$VPS" bash <<'REMOTE'
set -euo pipefail
cd ~/watranscribe

echo "--- git pull ---"
git pull

echo "--- venv sync ---"
.venv/bin/pip install -q -e .

echo "--- syntax check ---"
.venv/bin/python -m compileall -q app/ wsgi.py

echo "--- restarting service ---"
systemctl --user restart transcribe.service

echo "--- status ---"
systemctl --user status transcribe.service --no-pager -l | head -6
REMOTE

echo ""
echo "Done. Check https://transcribe.flyboybyte.com"
