---
name: agent-memory
description: Persist a durable convention, term, or stack law after self-review, PR comments, or a user correction. Use when verdict.json has metadata[], a review says agents keep missing X, or a domain term was resolved. Skip one-ticket acceptance criteria and style nits.
---

# Agent memory

Feedback is wasted if the next session repeats the same miss. Prefer the **harness** over hand-editing so path-scoped rules stay `alwaysApply: false` and secrets never land in git.

## Structured path (preferred)

1. On self-review, put durable misses in `verdict.json` as `metadata[]` (reviewer may only flag; parent may fill):

```json
{
  "verdict": "good",
  "summary": "one sentence",
  "risks": [],
  "metadata": [
    {
      "target": "agents",
      "text": "Isolation default is native git worktree; treehouse is opt-in.",
      "reason": "review assumed treehouse"
    },
    {
      "target": "rule",
      "path": ".claude/rules/python-tests.md",
      "globs": ["**/*.py"],
      "text": "Prefer pytest for new packages.",
      "reason": "PR comment"
    }
  ]
}
```

2. Conductor auto-applies when `agent_memory.auto_apply: true` (default): Claude `continue` after review, Cursor `step` after review / before ship, and `poll` before launching a PR fixer. Writes `memory-applied.json` in the run dir. Human PR comments go in `memory.json` (or `verdict.json` `metadata[]`); the fixer should still run `cli.py agent-memory` so it lands immediately instead of waiting for the next poll.
3. Manual: `python3 ~/.claude/hooks/dev-loop/cli.py agent-memory --repo REPO --verdict PATH` (or `--key TICKET`).

Targets: `agents` | `rule` | `context` | `readme`. Rules must be path-scoped (`globs`, never `always_apply`). Secrets/hooks paths are rejected. `durable: false` is rejected.

## When (still apply by hand if no verdict)

- User/PR review corrects how agents should work and you are not going through `verdict.json`.
- A domain term or hard-to-reverse decision was resolved (`domain-glossary`).

Skip: one-ticket AC, style nits, speculative rewrites, secrets, SessionStart text.

## Where (pick one)

| Signal | File | Rule |
| ------ | ---- | ---- |
| Convention every future agent on **this repo** must keep | `AGENTS.md` / `CLAUDE.md` | Harness appends under `## Agent memory`. |
| Stack law missing for a path | path-scoped `.claude/rules` / `.cursor/rules` | `alwaysApply: false` + `globs`. |
| Domain term | `CONTEXT.md` via `domain-glossary` | Glossary only. |
| Hard to reverse + surprising + real trade-off | `docs/adr/` via `domain-glossary` | Skip unless all three. |
| Install / usage / public API would be wrong | `README.md` | That case only. |

Reviewer is read-only on metadata files. Parent writes `metadata[]` or calls the CLI.

## Do not

- Invent ADRs or always-on rules.
- Stow notes into SessionStart or CLAUDE.md tax.
- Update conductor secrets, hooks, or `~/.config/dev-conductor/secrets.env`.
- Copy skill bodies into AGENTS.md.
- Treat `SPEC_APPROVED` as ticket-done or chat as the source of Jira AC.
