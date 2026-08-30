---
name: systematic-debugging
description: Use when hitting a bug, test failure, or unexpected behavior, before proposing a fix. Find root cause first.
---

# Systematic debugging

Do not patch symptoms. Complete investigation before changing code.

**Iron law:** no fix until Phase 1 is done.

## Phase 1 — root cause

1. Read the full error (status, stack, line, stderr).
2. Reproduce, or gather enough evidence if it is intermittent.
3. Check what changed (diff, last green, env).
4. Form one hypothesis. Add a log or failing test that would prove it.

## Phase 2 — pattern

Is this a known class (nil, race, wrong cwd, stale config, timeout)? Reuse that playbook. Do not cargo-cult an unrelated fix.

## Phase 3 — fix

Smallest change that addresses the cause. Add or keep a regression test.

## Phase 4 — prove

Run the command that failed. Show the output. Then check one nearby path that should still work.

If four attempts fail, stop and report: what you observed, what you ruled out, the next probe.
