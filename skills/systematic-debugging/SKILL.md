---
name: systematic-debugging
description: Find root cause before changing code. Use when a test fails, verify.log is red, a bug appears, or behavior is unexpected. Do not propose a patch until Phase 1 is done.
---

# Systematic debugging

A symptom patch (catch-all, skip the test, retry until green) usually hides the same bug for the next ticket. Spend the investigation **before** the edit.

## Phase 1 — root cause

1. Read the full error (status, stack, line, stderr). In `/dev-loop`, start with `verify.log` in the run dir if it exists.
2. Reproduce, or gather enough evidence if it is intermittent.
3. Check what changed (diff, last green, env, handshake stage).
4. Form **one** hypothesis. Add a log or failing test that would prove it.

## Phase 2 — pattern

Is this a known class (nil, race, wrong cwd, stale config, timeout, mocked-out unit)? Reuse that playbook. Do not cargo-cult an unrelated fix.

## Phase 3 — fix

Smallest change that addresses the cause. Keep or add a regression test at a **spec seam**. Do not rewrite tests to match leftover production code unless they contradict `spec.md` or fail to compile from syntax/IO mistakes.

## Phase 4 — prove

Run the command that failed. Show the output. Then check one nearby path that should still work. Then `verify-before-done`.

If four attempts fail, stop and report: what you observed, what you ruled out, the next probe. In `/dev-loop`, still write honest status; do not invent `STAGE_DONE` on a red suite.

## Example (shape)

Red: `assert response.status_code == 200` got 500, traceback in `health.py` line 12 `KeyError: 'status'`. Hypothesis: handler returns a dict without `status`. Probe: read that handler only after the traceback names it — do not Grep the tree “for context.” Fix the missing key; re-run the one test, then the suite.
