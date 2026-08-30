---
name: story-spec
description: Turn a Jira story into a technical spec via grill. Use in the spec stage of /dev-loop. Do not implement.
---

# Story spec

1. Load `prompt-contract` and `design-tree-interview`.
2. Read Jira markdown in the prompt or `issue.md` in the run dir.
3. Load repo-memory `INDEX.md` + `contracts.md` under `~/.config/dev-conductor/dev-loop/memory/<repo>/`. Explore only if missing/invalid.
4. Grill. Lock **seams** (public APIs to test), acceptance cases, non-goals, and data shape. Do not design internals.
5. Write `spec.md` in the run dir (`…/runs/KEY/spec.md`) with: summary, seams, Given/When/Then cases, non-goals.
6. Ask the user to approve **the spec**. On yes, write `SPEC_APPROVED` and `APPROVED`, then `SESSION_DONE` and `STAGE_DONE` in that run dir. `APPROVED` means spec accepted, not that the ticket is done.

Do not write application code. Do not open a PR.

If the Jira issue is UI/UX (screens, layout, visual QA), you may load skill `lavish-ui` (spike). Keep AC in this `spec.md`. Do not replace the ticket with HTML.
