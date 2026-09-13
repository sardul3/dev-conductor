---
name: token-playbook
description: Put procedures in skills, stack law in path-scoped rules, and keep always-on files small. Use when shrinking CLAUDE.md or AGENTS.md, choosing skills vs rules vs MCP, compressing tool output, or cutting Cursor always-apply rules.
---

# Token playbook

Always-on text is paid on every turn. Prefer lazy load.

## Where things go

| Thing | Put it | Loads |
| ----- | ------ | ----- |
| Facts every session needs | Root `CLAUDE.md` / `AGENTS.md` | Every turn. Target **< 200 lines / ~500 tokens** |
| Procedures | Skills (`SKILL.md`) | When invoked or relevant |
| Language/stack law | `.claude/rules/*.md` or `.cursor/rules/*.mdc` with globs | When a matching file is read |
| Unscoped / `alwaysApply: true` rules | Do not | Same tax as CLAUDE.md |

Parent `CLAUDE.md` walks **up** from cwd. A fat file in `~/dev/CLAUDE.md` taxes every repo under `~/dev`.

Do not paste `/dev-loop` skill bodies into `AGENTS.md`. Handshake and “no Jira MCP” belong in a short always-on file; stage playbooks stay in skills.

## Work vs grill

- Grill / enrich / `story-spec`: full sentences. Cursor Agent: **AskQuestion** (recommended first, ≤4 options). Claude enrich: `AskUserQuestion` or numbered markdown. No terse contract.
- Work session (launched `claude --model`, or `/dev-loop` writer): short contract in the **prompt**, plus `PROMPT_ENRICH_WORK_SESSION=1` on Claude. Depth words (`thorough`, `walk me through`, `tutorial`) back the hook off.

Do not install an always-on “be brief” skill. That fights interviews. Pattern from [denfry/claude-skills token-efficiency](https://github.com/denfry/claude-skills) (measured shorter replies); we scoped it to the work session only.

## Tool output

A 10k-line test log in context is worse than another prompt slot. `compress_output.py` (PostToolUse, Bash) replaces huge pytest/gradle/jest logs with **failures only** via `updatedToolOutput`.

## MCP

Unused MCP **schemas** load every session. User-scoped servers in `~/.claude.json` cannot be “off by default” reliably ([issue #35591](https://github.com/anthropics/claude-code/issues/35591)).

- Keep Jira + IdentityIQ **out** of user scope. Enable per repo with `claude/mcp/enable-project-mcp.sh` if you must.
- `/dev-loop` uses Jira REST + `gh`, not those MCPs.
- `/mcp` is per-session and easy to forget.

## Skills vs agents

Skill **descriptions** sit in a catalog; bodies load when relevant. Agent **descriptions** in `~/.claude/agents/` are always-on in the Task picker. Keep **few** agents (`code-reviewer`, `debugger`, `design-lead`). Put long procedures in skills.

## Cursor

A Java/Temporal **User Rule** with always-apply is the same tax. Use `.cursor/rules/*.mdc` with `globs` and `alwaysApply: false`.
