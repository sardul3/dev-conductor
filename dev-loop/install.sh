#!/usr/bin/env bash
# Install dev-loop CLI, SessionStart keys hook, test-writer deny hook, slash command.
# Merges hooks; does not wipe CCR env / apiKeyHelper.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_DEST="${HOME}/.claude/hooks/dev-loop"
CMD_DEST="${HOME}/.claude/commands"
LEGACY_CFG="${HOME}/.config/mac-ai-setup"
CFG_HOME="${HOME}/.config/dev-conductor"
if [[ -d "${LEGACY_CFG}" && ! -d "${CFG_HOME}" ]]; then
  mv "${LEGACY_CFG}" "${CFG_HOME}"
  echo "migrated ${LEGACY_CFG} -> ${CFG_HOME}"
fi
CFG_DEST="${CFG_HOME}/dev-loop"
SETTINGS="${HOME}/.claude/settings.json"

mkdir -p "${HOOK_DEST}" "${CMD_DEST}" "${CFG_DEST}"
cp "${ROOT}/dev-loop/"*.py "${HOOK_DEST}/"
chmod +x "${HOOK_DEST}/cli.py" "${HOOK_DEST}/session_start.py" "${HOOK_DEST}/deny_impl.py" "${HOOK_DEST}/fake_jira.py"
cp -R "${ROOT}/dev-loop/eval_templates" "${HOOK_DEST}/"
cp -R "${ROOT}/dev-loop/testdata" "${HOOK_DEST}/"
cp "${ROOT}/dev-loop/config.yaml.example" "${CFG_DEST}/config.yaml.example"
cp "${ROOT}/dev-loop/config.test.yaml" "${CFG_DEST}/config.test.yaml"
cp "${ROOT}/claude/commands/dev-loop.md" "${CMD_DEST}/dev-loop.md"
if [[ ! -f "${CFG_DEST}/config.yaml" ]]; then
  cp "${ROOT}/dev-loop/config.yaml.example" "${CFG_DEST}/config.yaml"
  echo "wrote ${CFG_DEST}/config.yaml — set jira.project"
fi

python3 - "${SETTINGS}" "${HOOK_DEST}" "${ROOT}/claude/prompt-enrich" << 'ENDMERGE'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
hook_dest = Path(sys.argv[2])
sys.path.insert(0, sys.argv[3])
from merge_settings import merge_hook

if settings_path.is_file():
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
else:
    data = {}
    settings_path.parent.mkdir(parents=True, exist_ok=True)
session_cmd = f"python3 {hook_dest / 'session_start.py'}"
deny_cmd = f"python3 {hook_dest / 'deny_impl.py'}"
data = merge_hook(data, "SessionStart", session_cmd)
data = merge_hook(data, "PreToolUse", deny_cmd, matcher="*")
settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("merged SessionStart + PreToolUse into", settings_path)
ENDMERGE

# skills
"${ROOT}/claude/prompt-enrich/install-skills.sh"
"${ROOT}/cursor/dev-loop/install.sh"

python3 "${HOOK_DEST}/cli.py" install-poller || true

echo
echo "dev-loop installed."
echo "  cli: python3 ${HOOK_DEST}/cli.py"
echo "  slash: /dev-loop KEY"
echo "  poll: python3 ${HOOK_DEST}/cli.py poll"
echo "  config: ${CFG_DEST}/config.yaml"
echo "  secrets: ~/.config/dev-conductor/secrets.env (ATLASSIAN_*)"
echo "CCR env in ~/.claude/settings.json was left in place."
