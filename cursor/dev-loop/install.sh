#!/usr/bin/env bash
# Cursor-first: CLI copy, all skills, .mdc rules, sessionStart + deny hooks.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.stderr.write(
        f"dev-conductor needs Python 3.10+ (this is {sys.version.split()[0]}). "
        "Install python@3.12 or pyenv, then re-run.\n"
    )
    raise SystemExit(1)
PY

HOOK_DEST="${HOME}/.claude/hooks/dev-loop"
CFG_HOME="${HOME}/.config/dev-conductor"
CFG_DEST="${CFG_HOME}/dev-loop"
DEST="${HOME}/.cursor/skills"
AGENTS="${HOME}/.agents/skills"
RULES="${HOME}/.cursor/rules"
CUR_HOOKS="${HOME}/.cursor/hooks/dev-loop"

mkdir -p "${HOOK_DEST}" "${CFG_DEST}" "${DEST}" "${AGENTS}" "${RULES}" "${CUR_HOOKS}"
cp "${ROOT}/dev-loop/"*.py "${HOOK_DEST}/"
rm -rf "${HOOK_DEST}/brief"
cp -R "${ROOT}/dev-loop/brief" "${HOOK_DEST}/brief"
chmod +x "${HOOK_DEST}/cli.py" "${HOOK_DEST}/session_start.py" "${HOOK_DEST}/deny_impl.py" "${HOOK_DEST}/fake_jira.py"
cp -R "${ROOT}/dev-loop/eval_templates" "${HOOK_DEST}/"
cp -R "${ROOT}/dev-loop/testdata" "${HOOK_DEST}/"
cp "${ROOT}/dev-loop/config.yaml.example" "${CFG_DEST}/config.yaml.example"
cp "${ROOT}/dev-loop/config.test.yaml" "${CFG_DEST}/config.test.yaml"
if [[ ! -f "${CFG_DEST}/config.yaml" ]]; then
  cp "${ROOT}/dev-loop/config.yaml.example" "${CFG_DEST}/config.yaml"
  python3 - "${CFG_DEST}/config.yaml" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
p.write_text(text.replace("agent: claude", "agent: cursor", 1), encoding="utf-8")
PY
  echo "wrote ${CFG_DEST}/config.yaml with runtime.agent: cursor — set jira.project"
fi

shopt -s nullglob
for d in "${ROOT}/skills"/*; do
  [[ -d "${d}" && -f "${d}/SKILL.md" ]] || continue
  n="$(basename "${d}")"
  rm -rf "${DEST}/${n}" "${AGENTS}/${n}"
  cp -R "${d}" "${DEST}/${n}"
  cp -R "${d}" "${AGENTS}/${n}"
  echo "cursor skill ${n}"
done

cp "${ROOT}/cursor/dev-loop/rules/dev-loop.mdc" "${RULES}/dev-loop.mdc"
if [[ -d "${ROOT}/.envfiles/rules/cursor" ]]; then
  for f in "${ROOT}/.envfiles/rules/cursor/"*.mdc; do
    [[ -f "${f}" ]] || continue
    cp "${f}" "${RULES}/$(basename "${f}")"
    echo "cursor rule $(basename "${f}")"
  done
fi

cp "${ROOT}/cursor/dev-loop/hooks/"*.py "${CUR_HOOKS}/"
chmod +x "${CUR_HOOKS}/"*.py
SESSION_CMD="python3 ${CUR_HOOKS}/session_start_cursor.py"
DENY_CMD="python3 ${CUR_HOOKS}/deny_read_cursor.py"
python3 "${ROOT}/cursor/dev-loop/merge_hooks.py" "${HOME}/.cursor/hooks.json" "${SESSION_CMD}" "${DENY_CMD}"

BIN="${HOME}/.local/bin"
mkdir -p "${BIN}"
cp "${ROOT}/dev-loop/bin/dev-loop" "${BIN}/dev-loop"
chmod +x "${BIN}/dev-loop"

CMD_DEST="${HOME}/.cursor/commands"
mkdir -p "${CMD_DEST}"
cp "${ROOT}/cursor/commands/dev-loop.md" "${CMD_DEST}/dev-loop.md"

ZSHRC="${HOME}/.zshrc"
touch "${ZSHRC}"
if ! grep -q 'alias dl='\''dev-loop'\''' "${ZSHRC}"; then
  printf '\n# dev-conductor\nalias dl='\''dev-loop'\''\n' >> "${ZSHRC}"
  echo "appended alias dl=dev-loop to ${ZSHRC}"
fi
if ! grep -q '\.local/bin' "${ZSHRC}"; then
  printf 'export PATH="$HOME/.local/bin:$PATH"\n' >> "${ZSHRC}"
  echo "appended ~/.local/bin to PATH in ${ZSHRC}"
fi

echo "Cursor port installed."
echo "  Agent chat: /dev-loop KEY   (reload Cursor window if missing)"
echo "  terminal:   dev-loop start KEY --repo ~/dev/YOUR-CLONE"
echo "  alias:      dl"
echo "  config:     ${CFG_DEST}/config.yaml  (runtime.agent: cursor)"
echo "  secrets:    ~/.config/dev-conductor/secrets.env (ATLASSIAN_*)"
echo "  guide:      cursor/README.md"
