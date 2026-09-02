---
name: story-spec
description: Turn a Jira story into spec.md (seams, Given/When/Then, non-goals) via an in-chat grill, then wait for the user to approve. Use whenever /dev-loop is in the spec stage, the user names a ticket key (ASE-12, LAB-1), or asks to spec/grill a Jira story. Do not implement or open a PR.
---

# Story spec

This is the **requirements lock** for `/dev-loop`. `test-writer` may only test the seams you write here. Vague seams produce either no tests or tests that spy on internals.

Stay in **this chat**. Do not run `launch-clean-claude.sh`. Do not follow `prompt-contract` handoff (that starts an implement session). For how to ask questions, load `design-tree-interview` and use **spec mode** (empty frontier → write `spec.md`, stop).

## Inputs

Run dir: `~/.config/dev-conductor/dev-loop/runs/KEY/` (`issue.md`, optional `lavish.json`).

Repo memory (skip Explore if HASH is fresh): `~/.config/dev-conductor/dev-loop/memory/<repo-folder>/INDEX.md` and `contracts.md`.

## Procedure

1. Read `issue.md` (or the Jira markdown in the prompt) and memory files.
2. Grill with `design-tree-interview` **spec mode**. Facts (existing routes, OpenAPI, test command) → look up. Product choices → ask, with a recommended answer each time.
3. Lock **seams** (public APIs to test), acceptance cases, non-goals, and data shape. Do not design class internals.
4. Write `spec.md` in the run dir using the template below.
5. Ask the user to approve **the spec** (AskQuestion). `SPEC_APPROVED` means the spec is accepted, not that the ticket is done.
6. **Only after they say yes:** write `SPEC_APPROVED`, `APPROVED`, `SESSION_DONE`, and `STAGE_DONE` in the run dir, then:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py step KEY
```

If they reject, revise `spec.md` and ask again. Never write `SPEC_APPROVED` because `spec.md` exists.

Do not write application code. Do not git commit. Do not open a PR. Do not invent `AGENTS.md` / rules here (`agent-memory` after review).

If `lavish.json` has `enabled: true` **and** the issue is UI/UX, load `lavish-ui`. Keep acceptance criteria in this `spec.md`; HTML is collaboration, not the contract.

## spec.md template

Use this exact heading structure. Fill every section; use `_none_` rather than omitting.

```markdown
# KEY — short title

## Summary
One paragraph: who, what observable behavior, why (from Jira).

## Seams
Public APIs the tests will call (HTTP route, exported function, message type). One bullet per seam. No private helpers.

## Acceptance
### Case 1 — <name>
- **Given** …
- **When** …
- **Then** … (status, body, error)

## Non-goals
What this ticket will not do.

## Data shape
Request/response or event fields that tests may assert. Optional `_none_`.

## Open questions
Unresolved product choices, or `_none_` after grill.
```

## Example (shape, not a mandate for every stack)

For a health probe story, seams and cases look like this — copy the **shape**, not the stack:

```markdown
# LAB-1 — Health check endpoint

## Summary
Operators need an unauthenticated GET that k8s can probe.

## Seams
- `GET /health`

## Acceptance
### Case 1 — liveness
- **Given** the app is running
- **When** `GET /health` with no auth
- **Then** HTTP 200 and JSON `{"status":"ok"}`

## Non-goals
Auth, extra fields, other routes.

## Data shape
`status` string, exactly `ok`.

## Open questions
_none_
```
