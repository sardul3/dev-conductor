#!/usr/bin/env bash
# Opt-in: install path-scoped stack rules from .envfiles/rules.
# Does not rewrite ~/.claude/CLAUDE.md. Skips git.md (unscoped).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RULES="${ROOT}/rules"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${HOME}/.config/dev-conductor/backups/envfiles-rules-${STAMP}"
mkdir -p "${BACKUP}" "${HOME}/.claude/rules" "${HOME}/.cursor/rules"

install_text() {
  local src="$1" dest="$2"
  if [[ -f "${dest}" ]] && ! cmp -s "${src}" "${dest}"; then
    mkdir -p "${BACKUP}$(dirname "${dest}")"
    cp -a "${dest}" "${BACKUP}${dest}" 2>/dev/null || true
    echo "backed up ${dest}"
  fi
  cp "${src}" "${dest}"
  echo "installed ${dest}"
}

shopt -s nullglob
for f in "${RULES}"/*.md; do
  base="$(basename "$f")"
  [[ "${base}" == "README.md" || "${base}" == "git.md" ]] && continue
  if ! grep -q '^paths:' "$f"; then
    echo "skip unscoped ${base}"
    continue
  fi
  install_text "$f" "${HOME}/.claude/rules/${base}"
done

for f in "${RULES}/cursor/"*.mdc; do
  [[ -f "$f" ]] || continue
  install_text "$f" "${HOME}/.cursor/rules/$(basename "$f")"
done

echo
echo "Rules installed from ${RULES}"
echo "  claude: ~/.claude/rules/  (path-scoped)"
echo "  cursor: ~/.cursor/rules/  (alwaysApply: false)"
