#!/usr/bin/env bash
# Install this repo's skills into ~/.claude/skills (does not install mattpocock-skills).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${HOME}/.claude/skills"
mkdir -p "${DEST}"
for d in "${ROOT}/skills"/*; do
  [[ -d "$d" && -f "$d/SKILL.md" ]] || continue
  name="$(basename "$d")"
  rm -rf "${DEST}/${name}"
  cp -R "$d" "${DEST}/${name}"
  echo "installed ${name}"
done
echo "Done. Skills are yours (recreated behavior, not the upstream plugin)."
