# Token diet (lean CLAUDE.md, work-session brevity, log compress, MCP)

Date: 2026-08-29  
Status: implemented  
Repo: `mac-ai-setup`

## Goal

Cut always-on tokens. Keep interviews verbose. Make work sessions terse with a depth backoff. Compress huge Bash test logs. Stop Jira/IdentityIQ MCP schemas from loading on every job.

## Adopted from others (behavior, not a dump of their trees)

- Anthropic: CLAUDE.md < ~200 lines; procedures → skills; path-scoped `.claude/rules/` ([Steering Claude Code](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more), [CLAUDE.md docs](https://code.claude.com/docs/en/claude-md)).
- [denfry/claude-skills token-efficiency](https://github.com/denfry/claude-skills): ~8-line contract, UserPromptSubmit refresh, depth-request backoff. **We do not enable this on every session** (it fights grilling). Contract goes in the **launched** prompt; hook runs only if `PROMPT_ENRICH_WORK_SESSION=1`.
- [dmitriyyukhanov slim-claude-md mechanics](https://github.com/dmitriyyukhanov/claude-plugins/blob/main/plugins/claude-md-slim/skills/slim-claude-md/references/mechanics.md): unscoped rules = no savings; parent CLAUDE.md walks up.
- Claude Code hooks: `updatedToolOutput` replaces Bash stdout ([hooks](https://code.claude.com/docs/en/hooks.md)).
- MCP: user-scoped servers cannot be default-off ([#35591](https://github.com/anthropics/claude-code/issues/35591)). Move heavy servers to project `.mcp.json`.

## Components

| Unit | When |
| ---- | ---- |
| Lean `~/.claude/CLAUDE.md` | Every Claude Code session |
| `~/.claude/rules/java-spring-temporal.md` `paths:` | Java/Gradle reads |
| Thin `~/dev/CLAUDE.md` | Every `~/dev/*` session (parent walk) |
| `skills/token-playbook`, `ase-lifecycle` | Invoked |
| Work-session `## Work session` + `work_brevity.py` | Launched `claude` only |
| `compress_output.py` PostToolUse Bash | Huge test/build logs |
| `mcp_diet.py` | Strip jira/identityiq from `~/.claude.json` |
| Prompt-log proxy (`SessionStart` → `:3457`) | CCR only; log full system+user before send |

## Prompt log (for later system-prompt thinning)

Claude Code `UserPromptSubmit` only receives `user_prompt`. The bloated system prompt and tool schemas are on `POST /v1/messages`. A SessionStart hook starts a local reverse proxy and points the session at it (`CLAUDE_ENV_FILE`). Logs: `~/.claude/prompt-enrichment/prompt-logs/`. Do not commit them. `thin_body()` is a passthrough until we strip Claude Code’s default system for setup/routing tasks.

## Non-goals

- Do not vendor denfry’s full skill as always-on.
- Do not put terse rules in the enrich/grill inject.
- Do not wipe CCR `settings.json` env.
