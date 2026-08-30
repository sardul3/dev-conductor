---
name: test-writer
description: Write failing tests from a technical spec and public contracts only. Use in /dev-loop test-writer stage. Do not read implementation sources or write production code.
---

# Test-writer

Input: spec.md + contracts.md. Ticket key in the prompt.

Public-API tests only (mattpocock/sanity TDD): a test reads like a spec (“GET /health returns ok”) and survives refactors.

- Write Given/When/Then tests at the **seams listed in the spec**.
- Prefer one vertical slice per ticket (the story’s primary behavior). Extra cases only if the spec names them.
- Cover named error/edge paths in the spec (behavioral tests, not line-coverage theatre).
- Do not Read `src/main`, `lib`, or other implementation trees. Tests + OpenAPI/contracts only.
- Do not implement production code. Do not mock the unit under test into emptiness.
- Do not later “fix” tests to match buggy code except compile/syntax/simple IO or a spec contradiction.
- Do not git commit.
- When done, write `STAGE_DONE` in the run dir from the prompt.
