#!/usr/bin/env bash
# Install prompt-enrich hooks + skills. Stock Claude Code auth; no OpenRouter/CCR required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK_SRC="$(cd "$(dirname "$0")" && pwd)"
HOOK_DEST="${HOME}/.claude/hooks/prompt-enrich"
STATE_DEST="${HOME}/.claude/prompt-enrichment"
CLASSIFY="${HOOK_DEST}/classify.py"

mkdir -p "${HOOK_DEST}" "${STATE_DEST}/state" "${STATE_DEST}/runs"
for f in classify.py route_model.py launch_prep.py merge_settings.py compress_output.py \
  work_brevity.py mcp_diet.py plan_guard.py after_launch.py save_handoff.py \
  launch-clean-claude.sh model-router.yaml; do
  cp "${HOOK_SRC}/${f}" "${HOOK_DEST}/${f}"
done
cp "${HOOK_SRC}/model-router.yaml" "${STATE_DEST}/model-router.yaml"
chmod +x "${HOOK_DEST}/launch-clean-claude.sh"

"${HOOK_SRC}/install-skills.sh"
"${ROOT}/claude/install-agents.sh"

python3 "${HOOK_SRC}/merge_settings.py" \
  --settings "${HOME}/.claude/settings.json" \
  --classify "python3 ${CLASSIFY}" \
  --classify-timeout 15 \
  --brevity "python3 ${HOOK_DEST}/work_brevity.py" \
  --compress "python3 ${HOOK_DEST}/compress_output.py" \
  --plan-guard "python3 ${HOOK_DEST}/plan_guard.py" \
  --after-launch "python3 ${HOOK_DEST}/after_launch.py"

echo
echo "prompt-enrich installed (anthropic default)."
echo "  hook: ${CLASSIFY}"
echo "  launch: ${HOOK_DEST}/launch-clean-claude.sh"
echo "  profiles: ${STATE_DEST}/model-router.yaml"
echo "  agents: ~/.claude/agents/ (code-reviewer, debugger, code-simplifier)"
echo "Disable: PROMPT_ENRICH_DISABLE=1   Skip one prompt: /skip-enrich …"
echo "Force grill: /deep-ask …"
echo "Optional CCR/OpenRouter: PROMPT_ENRICH_BACKEND=ccr + model-router.ccr.yaml in ${HOOK_DEST}/"
echo "MCP diet (remove Jira/IIQ from every session): python3 ${HOOK_SRC}/mcp_diet.py"
