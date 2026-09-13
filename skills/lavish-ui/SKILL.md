---
name: lavish-ui
description: Collaborate on UI with Lavish (npx -y lavish-axi) when lavish.json says enabled and the Jira story is visual (screens, CSS, layout). Skip API-only tickets. Never replace spec.md acceptance criteria with HTML annotations.
---

# Lavish UI

HTML review is collaboration. `spec.md` Given/When/Then remains the contract `test-writer` will implement.

Config: `lavish.enabled` is `auto` (default, UI repos only), `on`, or `off`. Per-slug overrides in `lavish.repos`. The conductor writes `lavish.json` in the run dir (`enabled`, `reason`). If `enabled` is false, skip this skill.

Not a blocking `/dev-loop` stage. Do not fail ship if Lavish is missing. Do not install SessionStart hooks.

## When

`lavish.json` says enabled **and** the issue is UI/UX (screens, CSS, layout, visual QA).

## Do

1. `npx -y lavish-axi --help` and `npx -y lavish-axi playbook plan` (or `diagram` / `comparison`).
2. `npx -y lavish-axi design` before writing HTML.
3. Artifacts under `.lavish/`. Open with `npx -y lavish-axi path/to/file.html`.
4. `npx -y lavish-axi poll path/to/file.html`. Fold notes into `spec.md` or the implementation.
5. Keep the markdown spec as the contract.

## Do not

- Vendor the upstream skill body.
- Use Lavish for backend-only stories.
- `lavish-axi share` unless the user asks.
- Treat annotations as the system of record.

Upstream: https://github.com/kunchenguid/lavish-axi
