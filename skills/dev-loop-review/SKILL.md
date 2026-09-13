---
name: dev-loop-review
description: Staff review for a /dev-loop ticket. Spawn code-reviewer on the git diff, write verdict.json, then STAGE_DONE. Use after verify is green, when prompt-review.md exists, or the user says review this ticket before the PR. Do not open a PR or git commit.
---

# Dev-loop review

The CLI decides rewrite vs ship from `verdict.json`. An honest `needs_improvement` is useful; a rubber `good` ships bugs. After the rewrite cap, **the CLI** still ships and puts risks in the PR body — you do not. PR body is CLI-owned (Jira browse link, recipe commands, visual evidence from `runs/KEY/evidence/`; no spec excerpt). Verdict is a one-liner. Confirm snapshots exist before the ship step; do not open a PR.

## Who runs this

**Parent:** Task a **new** Agent with `prompt-review.md` (or this skill + the diff). Do not review from this chat’s implementation history.

**Child:** follow the rest. After `verdict.json`:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py step KEY
```

Run dir: `~/.config/dev-conductor/dev-loop/runs/KEY/`.

## Procedure

1. Spawn `code-reviewer` on `git diff` vs the default branch. Reuse `verify.log`; do not re-run the full suite (the conductor re-verifies after a pass).
2. Cover: real bugs / authz / secrets, **silent failures** (swallowed errors, fake fallbacks), **test gaps** on new branches, type/invariant holes, comment rot in the diff. Confidence ≥ 80 only.
3. Write `verdict.json`:

```json
{
  "verdict": "good",
  "summary": "one sentence",
  "risks": [],
  "metadata": []
}
```

`verdict` one of: `excellent`, `good`, `good-with-risks`, `needs_improvement`, `blocker`.

| Verdict | CLI next |
| ------- | -------- |
| `excellent` / `good` | Ship (after another verify) |
| `good-with-risks` / `needs_improvement` / `blocker` | Writer retry until `caps.review_retries`, then ship anyway with this file in the PR |

4. Durable convention miss (not a one-off bug) → `metadata[]` (`target` / `text` / optional `path` / `globs` / `reason`). Conductor applies when `agent_memory.auto_apply` is true. Load `agent-memory` only if you must apply by hand. Do not invent ADRs or always-on rules.
5. Write `SESSION_DONE` and `STAGE_DONE`.

Do not commit. Do not open a PR. Do not spawn extra marketplace agents.

## Example

```json
{
  "verdict": "needs_improvement",
  "summary": "GET /health swallows DB errors and still returns 200.",
  "risks": ["operators will not see probe failure"],
  "metadata": [
    {
      "target": "rule",
      "path": ".cursor/rules/python-http.mdc",
      "globs": ["**/*.py"],
      "text": "Health handlers must not catch-all Exception into HTTP 200.",
      "reason": "silent failure on LAB-1"
    }
  ]
}
```
