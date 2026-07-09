#!/usr/bin/env bash
# Daily scrape + push. Run from project root.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"

{
    echo "=== $(date) ==="
    # Load VPS-specific env vars (PG_HOST, PG_PORT, etc.)
    [ -f "$SCRIPT_DIR/.env" ] && set -a && source "$SCRIPT_DIR/.env" && set +a
    source .venv/bin/activate
    python -m pipelines.scrape_daily
    python -m pipelines.push_to_postgres
    echo "=== Finished $(date) ==="
} 2>&1 | tee "$LOG_FILE"
