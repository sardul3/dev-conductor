#!/usr/bin/env bash
# Install dev-conductor for Claude Code and Cursor.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.stderr.write(
        f"dev-conductor needs Python 3.10+ (this is {sys.version.split()[0]}). "
        "Install python@3.12 or pyenv, then re-run.\n"
    )
    raise SystemExit(1)
PY

WITH_ENRICH=0
for arg in "$@"; do
  case "$arg" in
    --with-enrich) WITH_ENRICH=1 ;;
  esac
done

"${ROOT}/dev-loop/install.sh"
"${ROOT}/claude/install-agents.sh"
if [[ "${WITH_ENRICH}" -eq 1 ]]; then
  "${ROOT}/claude/prompt-enrich/install.sh"
fi

echo
echo "dev-conductor installed."
echo "  Cursor:  see cursor/README.md   then  /dev-loop KEY  or  dev-loop start KEY --repo PATH"
echo "  Claude:  /dev-loop KEY"
echo "  config:  ~/.config/dev-conductor/dev-loop/config.yaml"
echo "  secrets: ~/.config/dev-conductor/secrets.env (ATLASSIAN_* only)"
if [[ "${WITH_ENRICH}" -eq 0 ]]; then
  echo "  optional: ./install.sh --with-enrich  (ad-hoc prompt grill for Claude Code)"
fi
