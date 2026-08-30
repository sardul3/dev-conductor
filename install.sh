#!/usr/bin/env bash
# Install the Jira-to-PR loop + prompt-enrich + loop agents/skills on this Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
"${ROOT}/claude/prompt-enrich/install.sh"
"${ROOT}/dev-loop/install.sh"
"${ROOT}/claude/install-agents.sh"
echo
echo "dev-conductor installed."
echo "  /dev-loop KEY"
echo "  python3 ~/.claude/hooks/dev-loop/cli.py"
echo "  config: ~/.config/dev-conductor/dev-loop/config.yaml"
echo "Path-scoped Java/ML/LLM rules: install from ~/dev/mac-ai-setup (./claude/memory/install.sh)"
