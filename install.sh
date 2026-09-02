#!/usr/bin/env bash
# Install the Jira-to-PR loop + prompt-enrich + loop agents/skills on this Mac.
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
"${ROOT}/claude/prompt-enrich/install.sh"
"${ROOT}/dev-loop/install.sh"
"${ROOT}/claude/install-agents.sh"
echo
echo "dev-conductor installed."
echo "  /dev-loop KEY"
echo "  python3 ~/.claude/hooks/dev-loop/cli.py step KEY   # Cursor"
echo "  python3 ~/.claude/hooks/dev-loop/cli.py continue KEY  # Claude"
echo "  config: ~/.config/dev-conductor/dev-loop/config.yaml"
