---
name: tdd
description: Test-first implementation at public seams. Use when implementing a feature or bugfix, in the /dev-loop writer stage after test-writer, or when the user says TDD / write tests first. Do not start production code until a test is red for the right reason.
---

# TDD

A test that is written after the code only records what you already built. A test written first states the behavior. `/dev-loop` splits that work: **test-writer** already added the red suite; this skill is how the **writer** turns it green without sneaking in extra production code.

## Loop mode (`/dev-loop` writer)

Tests already exist and should be red. Do **not** add a new test first unless `verify.log` shows a missing case from the spec.

1. Run the inferred test command. Confirm red is an assertion at a spec seam, not a compile error you caused.
2. **Green** — smallest production change that passes **one** failing case (one vertical slice).
3. **Refactor** — stay green. Then the next red test.
4. Do not rewrite tests to match leftover production code unless they contradict the spec or fail to compile from syntax/IO mistakes.
5. Work-session tone: load `implement-terse`. Do not git commit (the conductor ships).

This is still TDD: you are not allowed to implement behavior that has no failing test. The suite is the backlog, not a finished horizontal spec you ignore.

## Standalone mode (no conductor)

Write a failing test first. Watch it fail for the right reason. Then minimum code to pass. Do not write the whole suite then implement (that horizontal slice is what **test-writer** is for, inside `/dev-loop` only).

## Both modes

- Name tests Given/When/Then.
- Test at spec seams (HTTP handler, exported port, app CLI). Never private helpers, linters, or package-manager commands.
- Never `git add` `__pycache__` or `.venv`. New Python repo: add a standard `.gitignore` (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`).
- If you implemented first in standalone mode, delete the production change and start from the test unless the user forbids it.
- Grill / spec sessions: do not implement at all.
