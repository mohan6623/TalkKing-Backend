#!/usr/bin/env bash
# =============================================================
# TalkKing Backend — Production Deploy Script
# Usage: ./infra/deploy.sh [--skip-tests]
# =============================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

# ── Config ────────────────────────────────────────────────────
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$BACKEND_DIR/venv"
SKIP_TESTS=false

for arg in "$@"; do
  [[ "$arg" == "--skip-tests" ]] && SKIP_TESTS=true
done

# ── Pre-flight checks ─────────────────────────────────────────
info "Starting TalkKing deploy from: $BACKEND_DIR"
cd "$BACKEND_DIR"

[[ -f ".env" ]] || error "Missing .env file. Copy .env.example and fill in values."
[[ -f "requirements.txt" ]] || error "Missing requirements.txt"

# ── Git pull ──────────────────────────────────────────────────
info "Pulling latest code..."
git pull origin main || warn "Git pull failed — continuing with local code"

# ── Virtualenv ────────────────────────────────────────────────
info "Setting up Python virtualenv..."
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

info "Installing/upgrading dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── Run tests ──────────────────────────────────────────────────
if [[ "$SKIP_TESTS" == "false" ]]; then
  info "Running test suite..."
  python -m pytest tests/ -v --tb=short -q || error "Tests failed — aborting deploy"
  info "All tests passed."
else
  warn "Skipping tests (--skip-tests flag set)"
fi

# ── Create required directories ───────────────────────────────
info "Ensuring log directories exist..."
sudo mkdir -p /var/log/talkking /var/lib/talkking
sudo chown -R deploy:deploy /var/log/talkking /var/lib/talkking 2>/dev/null || true

# ── Reload Supervisor services ────────────────────────────────
info "Reloading Supervisor..."
if command -v supervisorctl &>/dev/null; then
  sudo supervisorctl reread
  sudo supervisorctl update

  # Graceful restart — celery last to finish in-flight tasks
  sudo supervisorctl restart talkking:talkking-api
  sleep 3
  sudo supervisorctl restart talkking:talkking-celery-worker

  info "Supervisor services restarted."
  sudo supervisorctl status talkking:
else
  warn "supervisorctl not found — skipping service restart"
fi

# ── Reload Nginx ──────────────────────────────────────────────
info "Reloading Nginx config..."
if command -v nginx &>/dev/null; then
  sudo nginx -t && sudo nginx -s reload
  info "Nginx reloaded."
else
  warn "Nginx not found — skipping"
fi

# ── Health check ──────────────────────────────────────────────
info "Waiting for API to be healthy..."
sleep 5
for i in {1..10}; do
  if curl -sf http://localhost:8000/health > /dev/null; then
    info "Health check passed."
    break
  fi
  [[ $i -eq 10 ]] && error "API did not become healthy in time."
  sleep 3
done

info "Deploy complete!"
