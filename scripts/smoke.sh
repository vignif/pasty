#!/usr/bin/env bash
set -euo pipefail

# Smoke test for Pasty app behind Caddy prefix and direct access.
# - Verifies base page loads
# - Verifies static CSS/JS reachable
# - Verifies Socket.IO HTTP polling handshake endpoint responds (HTTP 200/400 depending on transport)
# - Prints concise results and exits non-zero on failure

# Usage:
#   ./scripts/smoke.sh                # tests default direct http://127.0.0.1:8001
#   BASE_URL=http://127.0.0.1:8001 ./scripts/smoke.sh
#   BASE_URL=https://apps.francescovigni.com/pasty ./scripts/smoke.sh

BASE_URL=${BASE_URL:-"http://127.0.0.1:8001"}
TIMEOUT=${TIMEOUT:-5}

# Trim trailing slash
BASE_URL=${BASE_URL%/}

_red() { printf "\033[31m%s\033[0m\n" "$*"; }
_green() { printf "\033[32m%s\033[0m\n" "$*"; }
_yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

req() {
  local url="$1"; shift
  local code
  code=$(curl -ksS -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" || true)
  echo "$code"
}

need_200() {
  local url="$1" label="$2"
  local code
  code=$(req "$url")
  if [[ "$code" == "200" ]]; then
    _green "[OK] $label -> 200"
  else
    _red "[FAIL] $label -> $code (expected 200)"
    return 1
  fi
}

need_one_of() {
  local url="$1" label="$2"; shift 2
  local code expected
  code=$(req "$url")
  for expected in "$@"; do
    if [[ "$code" == "$expected" ]]; then
      _green "[OK] $label -> $code"
      return 0
    fi
  done
  _red "[FAIL] $label -> $code (expected one of: $*)"
  return 1
}

main() {
  _yellow "Testing BASE_URL=$BASE_URL"

  # 1) Root page
  need_200 "$BASE_URL/" "Root page"

  # 2) Static assets
  need_200 "$BASE_URL/static/style.css" "Static CSS"
  need_200 "$BASE_URL/static/app.js" "Static JS"
  need_one_of "$BASE_URL/static/logo.png" "Static Logo" 200 304

  # 3) Socket.IO HTTP endpoint (XHR/Polling handshake)
  # We can't open WebSocket with curl, but the polling GET should return 200 or 400 depending on params.
  # Try without params first (many servers return 400 Bad Request), accept 200 or 400.
  need_one_of "$BASE_URL/socket.io/" "Socket.IO base" 200 400
  need_one_of "$BASE_URL/socket.io/?EIO=4&transport=polling" "Socket.IO polling" 200 400

  # 4) README page
  need_200 "$BASE_URL/readme" "Readme page"

  _green "All checks passed."
}

main "$@"
