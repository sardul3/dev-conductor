---
name: lavish-ui
description: Spike only. Use Lavish (npx -y lavish-axi) when the Jira story is UI/UX visual work — layouts, HTML mockups, design review. Do not use for API-only tickets. Do not replace Jira acceptance criteria.
---

# Lavish UI (spike)

This is a **spike**, not a conductor stage. Do not fail `/dev-loop` if Lavish is missing. Do not install SessionStart hooks (`lavish-axi setup hooks`) — that tax is always-on.

Jira remains the source of requirements. Write AC into `spec.md` as Given/When/Then. Lavish is an extra visual loop on top.

## When

Issue type, labels, or summary clearly UI/UX (screens, CSS, component layout, visual QA). Otherwise skip.

## Do

1. `npx -y lavish-axi --help` and `npx -y lavish-axi playbook plan` (or `diagram` / `comparison` as needed).
2. `npx -y lavish-axi design` before writing HTML.
3. Write artifacts under the repo’s `.lavish/` (gitignored if the repo prefers). Open with `npx -y lavish-axi path/to/file.html`.
4. Poll for reviewer notes: `npx -y lavish-axi poll path/to/file.html`. Fold accepted notes into `spec.md` or the implementation — not as a replacement for the Jira ticket.
5. Keep the markdown spec. HTML is the collaboration surface, not the contract.

## Do not

- Vendor the upstream lavish skill body; run the CLI so instructions stay current.
- Use Lavish for backend-only stories.
- Publish with `lavish-axi share` unless the user asks (third-party host).
- Treat browser annotations as the system of record.

Upstream: https://github.com/kunchenguid/lavish-axi
Spike note: `docs/spikes/2026-08-30-lavish-ui.md`
