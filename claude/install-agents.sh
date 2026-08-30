#!/usr/bin/env bash
# Install Claude Code subagents into ~/.claude/agents (lazy Task picker; keep this set small).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/claude/agents"
DEST="${HOME}/.claude/agents"
mkdir -p "${DEST}"
for f in "${SRC}"/*.md; do
  [[ -f "$f" ]] || continue
  cp "$f" "${DEST}/$(basename "$f")"
  echo "installed agent $(basename "$f" .md)"
done
echo "Done. Agents live in ${DEST} (descriptions are always-on — do not dump a large set)."
