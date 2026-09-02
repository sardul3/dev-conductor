# Architecture discovery with `design-tree-interview`

Use this reference for new integrations, migrations, target-state designs, or any request whose facts are incomplete. Close material design gaps without asking about facts already available in the repository.

In this repo, `/grill` means `design-tree-interview` (alias `grill-deep-ask`). Do not look for a skill named `grill`.

## Invocation contract

Invoke `design-tree-interview` with a brief shaped like this:

```text
Mode: enterprise architecture discovery
Goal: complete the blocking inputs for an implementation-ready architecture pack.

Known confirmed facts:
- ...

Repository or document evidence:
- FACT-ID — path:line-line — what it supports — confidence

Accepted assumptions:
- ASM-ID — assumption — consequence — owner/revisit date

Conflicts or uncertainty:
- ...

Unanswered blocking topics, highest information gain first:
1. ...
2. ...

Ask a focused round of at most six questions. Do not repeat answered questions.
For a question the user cannot answer, offer one recommended default and one
meaningfully different alternative, with the consequence of each. Return a
short normalized answer summary and the next unresolved blockers.
```

After each round:

1. update `requirements`, `platform`, `components`, `relationships`, `ui_spec` when in scope, `decisions`, `assumptions`, `risks`, and `open_questions` in the canonical model;
2. mark each answer `confirmed`, `evidenced`, `assumed`, or `unresolved`;
3. remove questions made irrelevant by a new decision;
4. invoke `design-tree-interview` again only for remaining blockers.

Do not use a fixed questionnaire verbatim. Ask only what changes architecture, implementation, governance, risk, cost, or review scope.

## Blocking discovery domains

### Outcome and scope

- Business outcome, consumers, measurable success, deadline, budget envelope.
- Current state, target state, system boundary, exclusions, migration/cutover expectations.
- System of record, product owner, technical owner, platform owner, operations owner.
- Required diagram audience and decision the pack must enable.

### Workload and nonfunctional requirements

- Request/event volumes, payload sizes, concurrency, peaks, growth, batch windows.
- Availability SLO, latency targets, consistency, durability, RTO, RPO.
- Failure tolerance, dependency behavior, retry/idempotency, timeout, backpressure, DLQ.
- Environments, release frequency, rollback time, support model, maintenance windows.

### Data and integration

- Data entities and directions; producer/consumer ownership; API, event, file, or database integration.
- Classification, PII/PHI/PCI/secrets, residency, retention, deletion, audit, lineage.
- Contract/versioning, schema registry, replay, ordering, deduplication, reconciliation.
- External parties, rate limits, certificates, allowlists, private connectivity, SLAs.

### Identity and security

- Human and workload identities; authentication, authorization, tenant boundaries.
- Secret/key/certificate lifecycle; encryption in transit and at rest; CMK needs.
- Threat model, abuse cases, public exposure, privileged actions, break-glass access.
- Compliance frameworks, evidence expectations, segregation of duties, audit retention.

### Azure landing zone

- Tenant/management-group/application landing-zone ownership.
- Subscription and environment strategy, regions, availability zones, data residency.
- Hub-spoke or Virtual WAN, VNet/subnet ownership, address space, DNS, ingress, egress.
- Private Link, firewall, DDoS, WAF, NAT, on-premises/partner connectivity.
- Azure Policy, Defender, Sentinel, diagnostic settings, tagging, budgets, locks.

### Kubernetes/AKS when applicable

- Why Kubernetes is needed; cluster ownership; private/public API; tenancy and isolation.
- Namespace, RBAC, workload identity, secret delivery, ingress/egress, network policy.
- Replicas, probes, requests/limits, HPA/KEDA, PDB, topology spread, stateful storage.
- Pod Security Standards, admission policy, image provenance, registry, SBOM/signing.
- GitOps, upgrade channel, maintenance, node pools, autoscaler, backup/restore, DR.

### Delivery and operations

- IaC language and ownership; CI/CD/GitOps system; promotion and approval flow.
- Logs, metrics, traces, SLOs, alerts, dashboards, synthetic checks, runbooks.
- Capacity validation, load/chaos/restore testing, cost guardrails, FinOps ownership.
- Implementation phases, dependencies, rollout, coexistence, rollback, decommissioning.

### Product UI when applicable

- Personas, roles/claims, primary jobs, routes, deep links, entry/exit, back/refresh, session expiry, unsaved work.
- Existing design system/components/tokens; supported devices, browsers, breakpoints, input modes, locales, and content ownership.
- Information hierarchy, forms/tables/search, validation, permissions, destructive/bulk actions, confirmations, undo, help and recovery.
- Default/loading/empty/error/success/permission/offline/degraded states; focus movement, announcements, and available actions.
- UI-to-API/event bindings, cache/freshness, optimistic behavior, retry/idempotency, masking, and sensitive-data minimization.
- WCAG target, keyboard/screen-reader/high-contrast/zoom/reflow needs, test tooling, manual test ownership, and representative-user validation.
- Analytics events/properties, consent/privacy, frontend stack, state/data patterns, feature flags, observability, rollout, and test pyramid.

## Completion rules

A field is complete when it is confirmed by the user, evidenced by a named source, accepted as an assumption with consequence and owner, or explicitly non-applicable with rationale.

An open question is non-blocking only when the architecture can be implemented safely without its answer. Give every open question an owner, due or revisit date, and a stated consequence of delay.

Do not manufacture exact volumes, SLOs, compliance requirements, IP ranges, regions, retention periods, SKUs, owners, or costs. Recommended defaults remain assumptions until accepted.
