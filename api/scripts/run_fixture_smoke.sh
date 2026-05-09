#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SMOKE_HOST="${SMOKE_HOST:-127.0.0.1}"
SMOKE_PORT="${SMOKE_PORT:-8767}"
BASE_URL="${BASE_URL:-http://${SMOKE_HOST}:${SMOKE_PORT}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -n "${SMOKE_TMP_DIR:-}" ]]; then
  TMP_ROOT="$SMOKE_TMP_DIR"
  CLEAN_TMP=0
else
  TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/travel-planner-smoke.XXXXXX")"
  CLEAN_TMP=1
fi

SESSION_DATA_DIR="${SESSION_DATA_DIR:-$TMP_ROOT/sessions}"
METRICS_DATA_DIR="${METRICS_DATA_DIR:-$TMP_ROOT/metrics}"
LOG_FILE="$TMP_ROOT/uvicorn.log"

mkdir -p "$SESSION_DATA_DIR" "$METRICS_DATA_DIR"

if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "Smoke target already responds at $BASE_URL; choose SMOKE_PORT or stop the existing API." >&2
  exit 1
fi

api_pid=""
cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  if [[ "$CLEAN_TMP" == "1" ]]; then
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT INT TERM

cd "$API_DIR"
GEMINI_API_KEY="${GEMINI_API_KEY:-test-gemini}" \
TAVILY_API_KEY="${TAVILY_API_KEY:-test-tavily}" \
E2E_FIXTURE_MODE=1 \
SESSION_DATA_DIR="$SESSION_DATA_DIR" \
METRICS_DATA_DIR="$METRICS_DATA_DIR" \
uv run uvicorn main:app --host "$SMOKE_HOST" --port "$SMOKE_PORT" >"$LOG_FILE" 2>&1 &
api_pid=$!

ready=0
for _ in $(seq 1 60); do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    break
  fi
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "$ready" != "1" ]]; then
  echo "Smoke API did not become ready at $BASE_URL" >&2
  cat "$LOG_FILE" >&2 || true
  exit 1
fi

BASE_URL="$BASE_URL" PYTHON_BIN="$PYTHON_BIN" bash scripts/smoke_curl.sh
