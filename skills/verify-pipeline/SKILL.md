---
name: verify-pipeline
description: Run pre-production gates before a PR. Use when verifying a ticket, before commit or gh pr, or when /dev-loop reaches verify.
---

# Verify pipeline

The conductor runs this. A failed gate stops the run. The fixer may not edit the tests that define the bug, lower a coverage or PIT floor, or edit files outside the ticket. Smell auto-fix is capped (`verification.fix_cap`) and only touches files this ticket changed.

```bash
python3 dev-loop/cli.py verify --repo PATH
```

Risk class is `verification.risk_class`, or `risk-class` in the run dir, unless a protected path (auth, payment, migration, privacy) escalates the ticket to sensitive.

| Class | Gates |
| ----- | ----- |
| safe | Static, unit, diff coverage. No docker, browser, or diagrams. |
| normal | Static through boot, diff coverage, PIT on the diff (floor 75%), new CVEs, artifact bundle. |
| sensitive | All of that, property and fuzz by default, and a named person in `HUMAN_APPROVED`. No auto-fix. |

Static (parallel): API doc diff, contract tests, lint, banned comments, architecture, antipatterns. A comment needs `lint:allow-comment:` plus a reason.

Tests stop at the first red suite: unit, component, integration, functional, acceptance, regression, then property and fuzz on the changed module when those tests exist. Coverage is the diff, not the whole tree. PIT starts at 75% killed.

Boot runs only if the repo starts. Smoke is that health check. Browser runs only when the diff touches UI.

Snyk (or `verification.commands.security`) fails new CVEs in the diff or in a dependency this ticket added. Baseline ids in `.devloop/cve-baseline.json` are recorded.

Threat model and pen test are headings in `spec.md` for sensitive work, not a scanner. Formal proof is not a default stage.

The bundle is `verify-bundle/` in the run dir (logs, coverage, mutation, health, and diagrams when the diff is not safe or tiny). The PR opens only when `verify-result.json` says `pr_allowed`, and the body links the bundle.

Deploy, release, and post-release (canary, soak, chaos, RUM) are out of this command.

## Borrowed procedures

Encoded here, not copied as extra skills:

- `testing-quality-gates`, `mutation-testing-pit` (PIT on the diff, not 98%)
- `openapi-governance`, `openapi-first-change` (API doc diff and contract tests)
- `archunit-rules` (architecture check when a command is set)
- `supply-chain-security`, `secure-code-review` (new CVE vs baseline; report, do not rewrite the repo)
- `security-threat-modeling` (sensitive spec input)
- `review-pack-generation` (the bundle)
- `spring-boot-production-readiness` (health with boot, only if the repo starts)
- `ase-lifecycle` (sensitive stops for a person; do not deploy from the ticket)

Left unused: deploy, release, feature flags, Kubernetes, incident response, observability, and the poller. Those are after merge.
