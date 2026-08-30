---
name: tdd
description: Use when implementing a feature or bugfix, before writing production code. Test first, watch it fail, then implement. Vertical slices at public seams.
---

# TDD

Write a failing test first. Watch it fail for the right reason. Then write the minimum code to pass.

**Iron law:** no production code without a failing test first (non-trivial logic).

Inspired by [mattpocock/skills tdd](https://www.skills.sh/mattpocock/skills/tdd): tests verify **behavior at public seams**, not internals. One **vertical slice** (one test → enough code → next test). Do not write the whole suite then implement (horizontal slice).

## Cycle

1. **Red** — one test that states the behavior through a public API. Run it. Confirm it fails as expected.
2. **Green** — smallest change that passes. Do not reshape the test to match leftover production code.
3. **Refactor** — stay green. Extract duplication only after green.

## Rules

- Name tests Given/When/Then.
- Test at seams agreed in the spec (HTTP handler, service port). Never private helpers.
- Do not skip “just this once.”
- If you implemented first, delete it and start from the test (unless the user forbids it).
- Work sessions: `implement-terse`. Grill sessions: do not implement.
