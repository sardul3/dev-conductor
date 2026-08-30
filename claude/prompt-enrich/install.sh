#!/usr/bin/env bash
# Install prompt-enrich hooks + skills. Merges UserPromptSubmit; does not wipe CCR env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK_SRC="$(cd "$(dirname "$0")" && pwd)"
HOOK_DEST="${HOME}/.claude/hooks/prompt-enrich"
ROUTER_DEST="${HOME}/.claude/prompt-enrichment"
CLASSIFY="${HOOK_DEST}/classify.py"

mkdir -p "${HOOK_DEST}" "${ROUTER_DEST}/state" "${ROUTER_DEST}/runs"
cp "${HOOK_SRC}/classify.py" "${HOOK_DEST}/classify.py"
cp "${HOOK_SRC}/route_model.py" "${HOOK_DEST}/route_model.py"
cp "${HOOK_SRC}/sync_ccr_free_fallback.py" "${HOOK_DEST}/sync_ccr_free_fallback.py"
cp "${HOOK_SRC}/launch_prep.py" "${HOOK_DEST}/launch_prep.py"
cp "${HOOK_SRC}/merge_settings.py" "${HOOK_DEST}/merge_settings.py"
cp "${HOOK_SRC}/compress_output.py" "${HOOK_DEST}/compress_output.py"
cp "${HOOK_SRC}/work_brevity.py" "${HOOK_DEST}/work_brevity.py"
cp "${HOOK_SRC}/mcp_diet.py" "${HOOK_DEST}/mcp_diet.py"
cp "${HOOK_SRC}/plan_guard.py" "${HOOK_DEST}/plan_guard.py"
cp "${HOOK_SRC}/after_launch.py" "${HOOK_DEST}/after_launch.py"
cp "${HOOK_SRC}/save_handoff.py" "${HOOK_DEST}/save_handoff.py"
cp "${HOOK_SRC}/prompt_log.py" "${HOOK_DEST}/prompt_log.py"
cp "${HOOK_SRC}/prompt_log_proxy.py" "${HOOK_DEST}/prompt_log_proxy.py"
cp "${HOOK_SRC}/ensure_prompt_log_proxy.sh" "${HOOK_DEST}/ensure_prompt_log_proxy.sh"
cp "${HOOK_SRC}/launch-clean-claude.sh" "${HOOK_DEST}/launch-clean-claude.sh"
cp "${HOOK_SRC}/model-router.yaml" "${HOOK_DEST}/model-router.yaml"
cp "${HOOK_SRC}/model-router.yaml" "${ROUTER_DEST}/model-router.yaml"
chmod +x "${HOOK_DEST}/launch-clean-claude.sh" "${HOOK_SRC}/launch-clean-claude.sh"
chmod +x "${HOOK_DEST}/ensure_prompt_log_proxy.sh" "${HOOK_SRC}/ensure_prompt_log_proxy.sh"

"${HOOK_SRC}/install-skills.sh"
"${ROOT}/claude/install-agents.sh"

python3 "${HOOK_SRC}/merge_settings.py" \
  --settings "${HOME}/.claude/settings.json" \
  --classify "python3 ${CLASSIFY}" \
  --classify-timeout 15 \
  --brevity "python3 ${HOOK_DEST}/work_brevity.py" \
  --compress "python3 ${HOOK_DEST}/compress_output.py" \
  --plan-guard "python3 ${HOOK_DEST}/plan_guard.py" \
  --after-launch "python3 ${HOOK_DEST}/after_launch.py" \
  --session-start "bash ${HOOK_DEST}/ensure_prompt_log_proxy.sh"

# Lean CLAUDE.md + path-scoped rules (Java/ML/LLM/TS/k8s). No-op if memory/ was moved to mac-ai-setup.
if [[ -x "${ROOT}/claude/memory/install.sh" ]]; then
  "${ROOT}/claude/memory/install.sh"
elif [[ ! -f "${HOME}/.claude/CLAUDE.md" && -f "${ROOT}/claude/memory/user.CLAUDE.md" ]]; then
  cp "${ROOT}/claude/memory/user.CLAUDE.md" "${HOME}/.claude/CLAUDE.md"
  echo "wrote ~/.claude/CLAUDE.md (lean user layer)"
fi

echo
echo "prompt-enrich installed."
echo "  hook: ${CLASSIFY}"
echo "  brevity (work session only): ${HOOK_DEST}/work_brevity.py"
echo "  compress Bash logs: ${HOOK_DEST}/compress_output.py"
echo "  catalog: ${ROUTER_DEST}/model-router.yaml"
echo "  launch: ${HOOK_DEST}/launch-clean-claude.sh"
echo "  agents: ~/.claude/agents/ (code-reviewer, debugger, code-simplifier)"
echo "  prompt log proxy: SessionStart → :3457 → CCR :3456"
echo "    logs: ~/.claude/prompt-enrichment/prompt-logs/"
echo "CCR env and apiKeyHelper in ~/.claude/settings.json were left in place."
echo "Disable: PROMPT_ENRICH_DISABLE=1   Skip one prompt: /skip-enrich …"
echo "Prompt log off: PROMPT_LOG_DISABLE=1"
echo "Force grill: /deep-ask …"
echo "Backend override: PROMPT_ENRICH_BACKEND=ccr|anthropic"
echo "MCP diet (remove Jira/IIQ from every session): python3 ${HOOK_SRC}/mcp_diet.py"
