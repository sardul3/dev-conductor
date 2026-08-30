#!/usr/bin/env bash
# SessionStart: start the prompt-log proxy and point this session at it.
# Only when Claude Code already uses a local CCR gateway. Fail open.
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${PROMPT_LOG_DIR:-${HOME}/.claude/prompt-enrichment/prompt-logs}"
LISTEN_PORT="${PROMPT_LOG_LISTEN_PORT:-3457}"
PID_FILE="${HOME}/.claude/prompt-enrichment/prompt-log-proxy.pid"

if [[ "${PROMPT_LOG_DISABLE:-}" == "1" ]]; then
  exit 0
fi

mkdir -p "${LOG_DIR}" "${HOME}/.claude/prompt-enrichment"

set +e
UPSTREAM="$(python3 "${HOOK_DIR}/prompt_log.py" --session-check)"
status=$?
set -e
if [[ "${status}" != "0" || -z "${UPSTREAM}" ]]; then
  exit 0
fi

port_open() {
  python3 - "$1" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.3)
try:
    raise SystemExit(0 if s.connect_ex(("127.0.0.1", port)) == 0 else 1)
finally:
    s.close()
PY
}

if ! port_open "${LISTEN_PORT}"; then
  nohup python3 "${HOOK_DIR}/prompt_log_proxy.py" \
    --listen "127.0.0.1:${LISTEN_PORT}" \
    --upstream "${UPSTREAM}" \
    --log-dir "${LOG_DIR}" \
    >> "${LOG_DIR}/proxy.log" 2>&1 &
  echo $! > "${PID_FILE}"
  ok=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if port_open "${LISTEN_PORT}"; then
      ok=1
      break
    fi
    sleep 0.1
  done
  if [[ "${ok}" != "1" ]]; then
    exit 0
  fi
fi

if [[ -z "${CLAUDE_ENV_FILE:-}" ]]; then
  exit 0
fi

{
  echo "export ANTHROPIC_BASE_URL=http://127.0.0.1:${LISTEN_PORT}"
  echo "export ANTHROPIC_API_BASE_URL=http://127.0.0.1:${LISTEN_PORT}"
  echo "export CLAUDE_AGENT_API_BASE_URL=http://127.0.0.1:${LISTEN_PORT}"
  echo "export PROMPT_ENRICH_CLASSIFIER_URL=http://${UPSTREAM}"
} >> "${CLAUDE_ENV_FILE}"
exit 0
