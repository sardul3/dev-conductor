#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${HOME}/.cursor/skills"
AGENTS="${HOME}/.agents/skills"
RULES="${HOME}/.cursor/rules"
mkdir -p "${DEST}" "${AGENTS}" "${RULES}"
for n in dev-loop story-spec test-writer repo-memory dev-loop-review pr-comment-fixer jira-progress lavish-ui tdd implement-terse verify-before-done systematic-debugging code-review; do
  rm -rf "${DEST}/${n}" "${AGENTS}/${n}"
  cp -R "${ROOT}/skills/${n}" "${DEST}/${n}"
  cp -R "${ROOT}/skills/${n}" "${AGENTS}/${n}"
  echo "cursor skill ${n}"
done
cp "${ROOT}/cursor/dev-loop/rules/dev-loop.mdc" "${RULES}/dev-loop.mdc"
echo "Cursor port installed. CLI remains python3 ~/.claude/hooks/dev-loop/cli.py"
