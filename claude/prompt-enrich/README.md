# Prompt enrich

Classifier + model router + clean Claude Code launch. Spec: `docs/superpowers/specs/2026-08-29-prompt-enrichment-design.md`.

```bash
./claude/prompt-enrich/install.sh
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```

- New-task prompts inject skill names only (`prompt-contract` → grill → `launch-clean-claude.sh`).
- Follow-ups (`yes`, `continue`, `resume`, `proceed`, …), slash commands, and `<!-- PROMPT_CONTRACT_V1 -->` skip (deterministic).
- Other prompts: one tiny CCR classify call (Y/N). Timeout/error → skip (fail open). `/deep-ask` still forces grill. Classifier hook timeout is 15s. Decisions append to `~/.claude/prompt-enrichment/hook-log.jsonl`. During enrich, PreToolUse denies Explore/Task/Agent/Glob/Grep/plan mode.
- Work session prompt includes a short no-filler contract. `PROMPT_ENRICH_WORK_SESSION=1` enables depth-backoff; grill is unchanged.
- PostToolUse compresses huge Bash test logs to failures (`updatedToolOutput`).
- `PROMPT_ENRICH_DISABLE=1` turns enrich + brevity + compress off. `/skip-enrich` skips one prompt. `/deep-ask` forces grill.
- `PROMPT_ENRICH_BACKEND=ccr|anthropic` overrides detection. Stock Anthropic launches unset CCR proxy env in the **child process only**.
- **Prompt log (SessionStart + local proxy):** Claude Code hooks never see system + tools. On CCR machines, SessionStart starts `prompt_log_proxy.py` on `:3457`, points the session at it, and forwards to CCR `:3456`. Each `POST /v1/messages` is written under `~/.claude/prompt-enrichment/prompt-logs/` (jsonl index + `raw/*.json` with full system + messages; tool schemas as name/size only). Secrets are redacted. Disable with `PROMPT_LOG_DISABLE=1`. Thinning is not on yet (`thin_body` is identity). If the jsonl file stays empty, Claude Code is still hitting `:3456` — set `ANTHROPIC_BASE_URL` to `http://127.0.0.1:3457` in that session or in settings (leave CCR itself on `:3456`).

CCR OpenRouter catalog is `:free` only. `python3 sync_ccr_free_fallback.py` sets CCR fallback to `model-chain` across those slugs. Do not add paid OpenRouter models.
