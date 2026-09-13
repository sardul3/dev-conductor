# Cursor-first conductor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cursor runs `/dev-loop` as a one-stage stepper (`cli.py step`) with hooks, all skills, and `.mdc` rules, without polling 24h; Claude `continue` stays blocking.

**Architecture:** Pure `plan_step` / `consume_done` in `dev-loop/step.py`. `runtime.agent: cursor` makes `continue` an alias of `step`. Cursor hooks adapt existing `session_start` / `deny_impl`. Install copies every `skills/*` and `.envfiles/rules/cursor/*.mdc`.

**Tech Stack:** stdlib Python 3.10+, unittest, bash install, Cursor `hooks.json` v1.

## Global Constraints

- Python 3.10+ required; installer exits if not.
- No Jira/GitHub MCP. Handshake: `SPEC_APPROVED` is human-only (unless `spec_auto_approve`).
- `continue --no-wait` unchanged (eval/full remainder). Do not reuse it for Cursor.
- Claude `settings.json` merge and prompt-enrich stay. Cursor-only install skips them.
- Do not commit unless the user asks.

---

### Task 1: `plan_step` / `consume_done` + no-sleep wait

**Files:**
- Create: `dev-loop/step.py`
- Create: `dev-loop/tests/test_step.py`
- Modify: `dev-loop/conductor.py` (`wait_session_done`)
- Modify: `dev-loop/tests/test_conductor.py`

**Interfaces:**
- Produces: `StepPlan(kind, stage)`, `plan_step(run, cfg, launched_stage)`, `consume_done(run, launched_stage)`, `wait_session_done` does not sleep when `agent==cursor`

- [ ] Failing tests for need_spec, setup test_writer, wait, consume→writer, cursor wait no sleep
- [ ] Implement `step.py` + wait short-circuit
- [ ] Tests pass

### Task 2: `step()` + CLI

**Files:**
- Modify: `dev-loop/step.py` (execute setup/verify/ship)
- Modify: `dev-loop/cli.py`
- Modify: `dev-loop/conductor.py` only if `step` needs `launch_prompt` imports

**Interfaces:**
- Produces: `step(key, repo, cfg) -> int`; `cli.py step KEY`; `continue` aliases `step` when `agent==cursor`

- [ ] Test CLI parser has `step`; continue routes cursor
- [ ] Implement

### Task 3: Cursor hook adapters

**Files:**
- Create: `cursor/dev-loop/hooks/session_start_cursor.py`
- Create: `cursor/dev-loop/hooks/deny_read_cursor.py`
- Create: `cursor/dev-loop/merge_hooks.py`
- Modify: `dev-loop/session_start.py` (`keys_message`)
- Modify: `dev-loop/tests/test_deny_impl.py`, `dev-loop/tests/test_session_start.py`

### Task 4: Install + skills + rules + command

**Files:**
- Modify: `cursor/dev-loop/install.sh`, `dev-loop/install.sh`, `install.sh`
- Modify: `skills/dev-loop/SKILL.md`, `story-spec`, `test-writer`, `prompt-contract`, `session-handoff`
- Modify: `cursor/dev-loop/rules/dev-loop.mdc`, `claude/commands/dev-loop.md`
- Modify: `.envfiles/AGENTS.md`

### Task 5: Verify

- [ ] `python3 -m unittest discover -s dev-loop/tests -v`
- [ ] Confirm Cursor install copies all skill dirs
