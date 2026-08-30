---
name: dev-loop-review
description: Staff review for /dev-loop. Spawn code-reviewer on the diff, write verdict.json. Use after verify is green, before the PR.
---

# Dev-loop review

1. Spawn `code-reviewer` on `git diff` vs the default branch. Reuse `verify.log`; do not re-run the full suite here (the conductor re-verifies after a pass).
2. The reviewer must cover: real bugs/authz/secrets, **silent failures** (swallowed errors, fake fallbacks), **test gaps** on new branches, type/invariant holes, and comment rot in the diff. Confidence ≥ 80 only.
3. Write `verdict.json` in the run dir:

```json
{"verdict": "good", "summary": "one sentence", "risks": []}
```

`verdict` one of: `excellent`, `good`, `good-with-risks`, `needs_improvement`, `blocker`.

excellent/good → ship. Anything else → writer (caps in config). After cap, still ship with risks in the PR.

4. Write `SESSION_DONE` and `STAGE_DONE`. If the verdict shows a **durable** convention miss (not a one-off bug), load `agent-memory` and update one relevant file; do not invent ADRs or always-on rules.

Do not commit. Do not open a PR. Do not spawn extra marketplace agents.
