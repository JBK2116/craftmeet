#!/usr/bin/env bash

# Craftmeet k6 WebSocket load-test runner
# Usage:
#   ./k6/run.sh                # Full test: setup → host (bg) → k6
#   ./k6/run.sh --quick        # Connection-only test (no host needed)
#   ./k6/run.sh --setup-only   # Only generate test data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

QUICK=false
SETUP_ONLY=false
# These are only used when --vus/--duration are explicitly passed.
# By default the k6 script uses its own staged ramp (20s up, 60s hold, 20s down).
VUS=""
DURATION=""
BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
PARTICIPANTS=100

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --quick           Connection-only test (no host needed).
  --setup-only      Only generate test-data.json, then exit.
  --vus N           Override: use fixed-VU mode with N VUs (skips staged ramp).
  --duration D      Used with --vus: test duration (e.g. 60s).
  --participants N  Number of unique participant tokens (default: 100).
                    Must be >= your peak VU count to avoid duplicate connections.
  --base-url URL    Backend base URL (default: $BASE_URL).
  -h, --help        Show this message.

By default the k6 script ramps 0→50 over 20s, holds 50 for 60s, then ramps
down.  To find your concurrency ceiling:

  $0 --participants 500                        # generate 500 unique tokens
  # Then edit k6/participant-load-test.js stages:
  #   { duration: "30s", target: 500 },
  #   { duration: "60s", target: 500 },
  #   { duration: "20s", target: 0 },

Examples:
  $0                                    # Full test with staged ramp
  $0 --vus 100 --duration 30s           # Constant 100 VUs for 30 s
  $0 --setup-only --participants 500    # Generate tokens for 500 users
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)       QUICK=true; shift ;;
    --setup-only)  SETUP_ONLY=true; shift ;;
    --vus)         VUS="$2"; shift 2 ;;
    --duration)    DURATION="$2"; shift 2 ;;
    --participants) PARTICIPANTS="$2"; shift 2 ;;
    --base-url)    BASE_URL="$2"; shift 2 ;;
    -h|--help)     usage ;;
    *)             echo "Unknown option: $1"; usage ;;
  esac
done

# 1. Setup
echo "=== [1/3] Setup ==="
python k6/setup.py \
  --participants "$PARTICIPANTS" \
  --base-url "$BASE_URL"

if $SETUP_ONLY; then
  echo "✓ Setup complete.  Data in k6/test-data.json"
  exit 0
fi

# 2. (Optional) Host driver
if $QUICK; then
  echo "=== [2/3] Skipping host driver (--quick mode) ==="
else
  echo "=== [2/3] Starting host driver in background ==="
  # Give the host enough time to cover the staged ramp (20+60+20 = 100s) plus buffer
  HOST_DURATION="$(echo "${DURATION:-120s}" | grep -oP '\d+' || echo 120)"
  python k6/host-driver.py \
    --base-url "$BASE_URL" \
    --duration "$HOST_DURATION" &
  HOST_PID=$!
  # Give the host time to connect and start the meeting
  sleep 3
  echo "  Host PID: $HOST_PID"
fi

# 3. Run k6
K6_SCRIPT="$SCRIPT_DIR/participant-load-test.js"

K6_ARGS=()
if [[ -n "$VUS" ]]; then
  K6_ARGS+=(--vus "$VUS")
  echo "=== [3/3] Running k6 (fixed ${VUS} VUs, ${DURATION:-60s}) ==="
else
  echo "=== [3/3] Running k6 (staged ramp from script) ==="
fi
if [[ -n "$DURATION" ]]; then
  K6_ARGS+=(--duration "$DURATION")
fi

k6 run "${K6_ARGS[@]}" "$K6_SCRIPT"

K6_EXIT=$?

# Cleanup
if [[ -n "${HOST_PID:-}" ]]; then
  echo "=== Stopping host driver (PID $HOST_PID) ==="
  kill "$HOST_PID" 2>/dev/null || true
  wait "$HOST_PID" 2>/dev/null || true
fi

echo "=== Done (k6 exit: $K6_EXIT) ==="
exit $K6_EXIT
