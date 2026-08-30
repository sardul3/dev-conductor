#!/usr/bin/env bash
# Write the skip-marked prompt and open a new Claude Code CLI terminal.
# Usage: launch-clean-claude.sh --file <handoff.md> [--session id] [--cwd dir] [--profile code] [--backend ccr|anthropic] [--override opus] [--dry-run]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=0
PASSTHRU=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    *) PASSTHRU+=("$1"); shift ;;
  esac
done

JSON="$(python3 "${DIR}/launch_prep.py" "${PASSTHRU[@]}")"
printf '%s\n' "${JSON}"
RUNNER="$(printf '%s' "${JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["runner_file"])')"
PROMPT="$(printf '%s' "${JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["prompt_file"])')"

echo "Prompt saved: ${PROMPT}"
echo "Work continues in a new Claude Code terminal. Do not implement in this session."

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "Dry run. Manual: bash ${RUNNER}"
  exit 0
fi

if PYTHONPATH="${DIR}" python3 -c 'import sys; from launch_prep import open_new_terminal; raise SystemExit(0 if open_new_terminal(sys.argv[1]) else 1)' "${RUNNER}"; then
  exit 0
fi

echo "Could not open a terminal. Run:"
echo "  bash ${RUNNER}"
exit 0
