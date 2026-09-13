# Cursor-first conductor (keep Claude)

Date: 2026-09-01
Status: implemented
Repo: `dev-conductor` at `~/Projects/dev-conductor`

## Goal

Make `/dev-loop KEY` a complete daily driver in **Cursor** without turning Cursor into a fake Claude launcher. Claude Code keep working. Spec stays a human gate. Jira REST + `gh` stay; no Jira/GitHub MCP.

## Constraint (reverses 2026-08-30 note)

The v1 spec said “Do not change Claude-only files to make Cursor work.” This spec **does** change shared conductor behavior when `runtime.agent` is `cursor`, and adds Cursor hooks. Claude hooks, slash command, and prompt-enrich stay as they are unless a shared function would otherwise wait forever.

## Why the current Cursor port fails

`launch_prompt` for `agent: cursor` writes `prompt-*.md` and returns. `continue_loop` then polls `STAGE_DONE` / `SESSION_DONE` for `wait_timeout_sec` (default **86400**). Nothing in Cursor is launched, so the CLI sits until timeout.

`continue --no-wait` is **not** the fix. If `wait` is false, `continue_loop` still walks **every** remaining stage in one process (test-writer → writer → verify → review → ship) without letting an agent work. That is eval/adapter behavior, not an interactive loop.

Cursor install copies **16 / 25** skills. `story-spec` still says load `prompt-contract` and `design-tree-interview`, which are omitted. Grill is thinner by installer choice, not by skill format.

Claude `SessionStart` / `PreToolUse` do not run in Cursor. Cursor **does** have `sessionStart`, `beforeReadFile`, and `preToolUse` user hooks (`~/.cursor/hooks.json`).

## Architecture

**Cursor agent is the conductor. CLI is a stepper plus side-effect commands.**

```
/dev-loop KEY
  → cli.py start KEY --repo PATH     # fetch, worktree, memory, write prompt-spec.md
  → this chat: story-spec grill
  → AskQuestion: approve spec?
       no  → stay on spec
       yes → write SPEC_APPROVED + APPROVED + STAGE_DONE
  → cli.py step KEY                  # next incomplete stage only, never polls
  → test-writer: new Agent (spec.md + contracts.md only)
       child writes tests + STAGE_DONE
  → cli.py step KEY                  # writer prompt; this chat implements
  → cli.py step KEY                  # verify in-process (no LLM)
       red → writer retry via step
  → cli.py step KEY                  # review Agent → verdict.json
  → cli.py step KEY                  # ship (git + gh)
```

Handshake files stay the source of truth under `~/.config/dev-conductor/dev-loop/runs/KEY/`.

| File | Who writes | When |
| ---- | ---------- | ---- |
| `STAGE_DONE` / `SESSION_DONE` | Agent (or stepper for in-process stages) | End of that stage. **Not** a human ritual. |
| `SPEC_APPROVED` / `APPROVED` | Agent **after** user confirms | Human spec gate. Never auto-write on `spec.md` appearing. |
| `verdict.json` | Review agent | End of review |
| `verify.log` | CLI `run_verify` | Verify stage |

`runtime.agent: cursor` default wait: **do not poll**. `wait_session_done` / `wait_file` short-circuit when agent is `cursor` (same as `agent: none` for waiting only — not for builtin adapters).

## CLI: `step`

Add `cli.py step KEY [--repo PATH]`.

One invocation does **exactly one** of:

1. If spec not approved → print run dir + “grill then write SPEC_APPROVED”; exit 2.
2. Else find first incomplete stage from `progress.md` / `state.json` / handshake files.
3. **Setup-only stages** (test-writer, writer, review, simplify): set `state.stage`, write `prompt-*.md`, clear previous `STAGE_DONE`/`SESSION_DONE`, print the prompt path, exit 0. Do not wait.
4. **In-process stages** (verify, evidence, ship, jira `on_pr`): run them, write handshake/progress, exit with their rc.

`continue KEY` with `agent: cursor` becomes an alias of `step` (one stage). Claude `continue` (default `agent: claude`) stays the blocking multi-stage loop.

Do not reuse `--no-wait` for this. That flag means “run the whole remainder without waiting,” which remains eval-only.

## Test-writer isolation

Primary: **new Cursor Agent** whose prompt is `test_writer_prompt(...)` only (spec + contracts + “do not Read implementation”). Parent chat does not Read `src/main` during that stage.

Secondary: user hook `beforeReadFile` (and `preToolUse` Read/Grep/Glob if payload includes path) calling existing `deny_impl.should_deny` when `state.stage == test-writer`. Cursor JSON out: `{ "permission": "deny", "agent_message": "..." }`. Fail open on hook errors.

A deny hook without a new Agent is not enough: impl can already be in context from earlier turns.

## SessionStart → Cursor `sessionStart`

Install `~/.cursor/hooks.json` `sessionStart` → adapter around `session_start.py`.

- Reuse `eligible()`, cache, `search_keys`.
- Cwd from Cursor hook payload (`workspace_roots` / cwd field — implement against the live stdin JSON; fall back to `os.getcwd()`).
- Output: `additional_context` with the same key list Claude prints. Fail silent (exit 0, no context) if secrets missing or ineligible.

Claude `SessionStart` merge in `~/.claude/settings.json` is unchanged.

## Skills

`cursor/dev-loop/install.sh` copies **all** `skills/*` (the 25 dirs), not a 16-name allowlist. Also `~/.agents/skills`.

Loop-facing rewrites (Cursor behavior, keep Claude commands valid where both exist):

- `story-spec`: grill in **this** chat via `prompt-contract` + `design-tree-interview`. Do not call `launch-clean-claude.sh`. On user yes → write `SPEC_APPROVED`, `APPROVED`, `STAGE_DONE`, `SESSION_DONE`. Then `cli.py step KEY`.
- `dev-loop`: Cursor path is `start` then `step` (never blocking `continue`). Repo picker unchanged (`repos --format json` + AskQuestion).
- `session-handoff` / `prompt-contract`: if Cursor (no `claude` launch script required), write handoff under `~/.config/dev-conductor/handoffs/` and spawn/instruct a **new Cursor Agent** with that file. If Claude, keep `save_handoff.py` + `launch-clean-claude.sh`.
- `test-writer`: “Parent must Task a new agent. Child writes tests + STAGE_DONE only.”
- `finish-branch`: still not used by ship; install it anyway so manual finishes match Superpowers.

Do not paste skill bodies into `AGENTS.md`.

## Rules

`.envfiles/rules/cursor/*.mdc` are already Cursor-valid (`alwaysApply: false`, globs). Cursor install **also** runs the cursor half of `.envfiles/install-rules.sh` (copy every `rules/cursor/*.mdc` → `~/.cursor/rules/`). Opt-in remains for Claude `~/.claude/rules/*.md`.

`cursor/dev-loop/rules/dev-loop.mdc` updates to: step CLI, handshake table, new-Agent test-writer, hooks paths. Still `alwaysApply: false`; trigger on `/dev-loop`, Jira key, “work this story.”

## Hooks layout (user-level)

```
~/.cursor/hooks.json          # version 1; merge, do not wipe
~/.cursor/hooks/dev-loop/
    session_start_cursor.py   # thin stdin adapter → session_start
    deny_read_cursor.py       # thin adapter → deny_impl.should_deny
```

CLI Python remains `~/.claude/hooks/dev-loop/` so Claude install stays one copy. Cursor skills keep calling that path. Cursor-only install **must copy the CLI** even if it skips prompt-enrich and Claude `settings.json` merge.

`./install.sh` (full): prompt-enrich + Claude loop hooks + Cursor install (skills, rules, hooks, CLI).

`./cursor/dev-loop/install.sh` (Cursor-first): CLI copy + all skills + cursor rules + Cursor hooks. Skip `merge_settings.py` for Claude prompt-enrich. Skip poller load unless `poller.enabled`.

## Config

Example yaml: `runtime.agent: cursor` documented; leave default `claude` so existing Claude machines do not change behavior on upgrade. Cursor install prints “set runtime.agent: cursor”.

`wait_timeout_sec` unused for cursor wait (no poll). Caps / worktree / `queue.max_active` / `agent_memory.auto_apply` unchanged.

Python: installer checks `python3 >= 3.10` and exits with a one-line fix if not (current macOS `/usr/bin/python3` is 3.9).

## Tests (failing first)

- `test_conductor.py`: `step` runs one stage; second `step` without STAGE_DONE re-prints same stage; after STAGE_DONE advances; spec-not-approved exits 2; cursor agent never sleeps on `wait_session_done`.
- `test_deny_impl.py`: Cursor adapter maps deny → `permission: deny`.
- `test_session_start.py` (extend): Cursor adapter returns additional_context JSON; ineligible → empty success.
- Install script test or golden list: Cursor skill dir names == all `skills/*`.
- Existing unittest suite still green. Eval (`builtin_adapters`, `agent: none`) unchanged.

## Out of scope

- Reimplementing prompt-enrich classify / plan_guard / prompt-log proxy in Cursor.
- Poller auto-merge, quality, evidence, lavish wiring (leave opt-in as today).
- Changing Jira to MCP.
- Committing this spec is optional; user git rule requires an explicit ask.

## Definition of done

1. Cursor-only install (no Claude Code) can: `start` → grill in Cursor → human spec yes → new-Agent test-writer → writer → verify → review → `gh pr`.
2. Claude `continue` still launches and waits when `runtime.agent: claude`.
3. `SPEC_APPROVED` is never written by `step` / `start` unless `spec_auto_approve` (eval/unattended only).
4. All skills and cursor `.mdc` rules are installed to `~/.cursor/`.
5. `sessionStart` lists keys; `beforeReadFile` denies impl reads in test-writer.
