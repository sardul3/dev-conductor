---
name: arch-studio
description: Design, review, and revise enterprise system integrations, cloud architectures, and implementation-ready UI specifications as one governed visual pack with multi-page draw.io diagrams, responsive wireframes, user flows, screen states, UI-to-API bindings, a clickable HTML review workspace, traceability, Azure governance, and Kubernetes production-readiness checks. Use for system integration, architecture diagrams, UI/UX technical specifications, repository mapping, design review, or visual implementation planning. Azure is the default cloud unless the user explicitly chooses another provider.
license: MIT
metadata:
  version: "1.1.0"
  default_cloud: azure
  output_model: architecture-and-ui-as-code
  compatibility: Cursor and Claude Code with Python 3.10+; discovery uses design-tree-interview (alias grill-deep-ask); diagrams.net is optional; the review chat bridge requires the claude CLI
---

# Arch Studio

Create an implementation-ready visual specification, not a decorative diagram. Keep one canonical architecture JSON model and derive every diagram and review artifact from it.

## Non-negotiable rules

- For an integration or incomplete design request, invoke `design-tree-interview` (alias `grill-deep-ask`; upstream called this `/grill`) before designing. Continue focused discovery until every blocking field in [references/discovery-grill.md](references/discovery-grill.md) is confirmed, evidenced, or explicitly accepted as an assumption.
- Inspect available repository and infrastructure evidence before asking questions that the code or configuration can answer. Never present inferred topology as observed fact.
- Default to Azure. Do not substitute Azure services when the user names another provider or requires cloud neutrality.
- Prefer the simplest design that meets the stated SLOs, scale, security, delivery, and operational constraints. Never introduce AKS, messaging, multi-region, service mesh, or another complex platform without a requirement or recorded rationale.
- Generate static artifacts only. Do not add CSS/SVG motion, canvas animation, animated GIFs, auto-advancing content, or decorative transitions.
- Every connection must have a meaningful label that includes the action or data and, when known, protocol, port, authentication, and synchronous/asynchronous behavior.
- Every view must have a visible title and an automatic or authored legend. Every component must expose purpose, owner, technology/service, criticality, data classification, controls, and evidence or confidence in the review workspace.
- Treat Azure and Kubernetes checks as evidence-based gates. Never claim a pass when blocking findings, expired waivers, or unresolved critical questions remain.
- Keep stable IDs when revising. Update the canonical model and regenerate; never hand-edit generated `.drawio`, HTML, reports, or receipts.

## Workflow

### 1. Establish scope and evidence

1. Read the request and relevant repository material. Search architecture docs, IaC, manifests, deployment configuration, API contracts, schemas, and runtime configuration first.
2. Record facts with evidence paths and confidence. Record conflicts as open questions; do not silently choose one source.
3. Create or update `<project>.arch.json` using [assets/architecture.schema.json](assets/architecture.schema.json) and [references/architecture-model.md](references/architecture-model.md).
4. For repository-derived facts, use repository-relative paths and line ranges or immutable commit references. Do not include secrets, credentials, or unredacted production data.

### 2. Run the discovery loop

Read [references/discovery-grill.md](references/discovery-grill.md). Invoke `design-tree-interview` (alias `grill-deep-ask`) with the known facts, evidence, assumptions, conflicts, and only the unanswered blocking topics. Ask in small, prioritized rounds; update the canonical model after each answer.

Do not finish discovery merely because the user does not know an answer. Offer a clearly labeled recommended default with its consequence, then record the user's acceptance as an assumption or decision. If `design-tree-interview` is unavailable, state that the required dependency is missing and ask whether direct discovery questions are acceptable before proceeding.

Discovery is complete only when:

- the business outcome, system boundary, actors, current state, target state, success measures, exclusions, and ownership are clear;
- traffic, availability, latency, scaling, RTO/RPO, environments, release, rollback, observability, support, and cost constraints are clear;
- data flows, classifications, retention, residency, encryption, identity, authorization, secrets, external parties, trust boundaries, and compliance constraints are clear;
- Azure landing-zone, subscription, region, network, DNS, ingress, egress, private connectivity, policy, tagging, and shared-service expectations are clear;
- when Kubernetes applies, cluster ownership, tenancy, namespaces, workload identity, ingress/egress, policies, workload security, scaling, disruption, upgrade, backup, and GitOps expectations are clear;
- every remaining unknown is explicitly non-blocking, owned, and visible in `open_questions`.
- when UI is in scope, personas/roles, primary jobs, routes, information hierarchy, design-system reuse, responsive breakpoints, content, validation, authorization, screen states, accessibility, analytics/privacy, frontend stack, API/data bindings, and acceptance tests are clear.

### 3. Select the diagram pack

Read [references/diagram-pack.md](references/diagram-pack.md). For a system-integration request, create the Standard Integration Pack unless the user asks for a smaller or comprehensive pack. Include only relevant views, but never omit a security/trust view or production deployment view for a production design.

At minimum, a production integration normally includes:

1. system context;
2. logical container/service architecture;
3. Azure deployment and network topology;
4. security, identity, and trust boundaries;
5. data flow and classification;
6. one critical-path sequence;
7. Kubernetes workload/runtime view when Kubernetes is used;
8. delivery/GitOps, observability, and recovery views when they materially affect implementation.

When UI is in scope, add relevant `user-flow`, `ui-wireframe`, and `ui-state-map` pages. Cover every declared breakpoint and each default, loading, empty, error, permission-denied, success, offline, or destructive-confirmation state that materially applies. Do not create pixel-polished decoration before task flow, content, state, authorization, and accessibility contracts are settled.

### 4. Design the target architecture

Read [references/design-quality.md](references/design-quality.md), then the provider/runtime references that apply:

- Azure: [references/azure-governance.md](references/azure-governance.md)
- Kubernetes or AKS: [references/kubernetes-review.md](references/kubernetes-review.md)

Use explicit architecture decisions for choices with material alternatives or consequences. Maintain requirement-to-component and requirement-to-control references. Include failure behavior, retry/idempotency, timeouts, backpressure, dead-letter handling, rollback, degradation, and recovery where relevant.

Use Azure-native services only when they are the best fit. State why a managed service, Kubernetes workload, serverless component, database, queue, cache, gateway, or network appliance is needed. Show ownership and platform/application responsibility boundaries.

### 4a. Specify the product UI when it is in scope

Read [references/ui-specification.md](references/ui-specification.md). Inspect the existing frontend, component library, routes, tokens, API clients, validation, authorization, tests, and analytics before proposing replacements. Reuse the product design system; use Fluent 2 only as the Azure-aligned default when no established system exists.

Treat `ui_spec` as part of the same architecture model. Link every screen and user flow to requirements, every data-bound region to an architecture component and connection contract, and every visible action to authorization and keyboard behavior. Define responsive layouts, semantic tokens, component contracts, screen states, focus and live announcements, route guards, back/refresh behavior, analytics privacy, frontend implementation choices, and automated/manual acceptance coverage.

Target WCAG 2.2 Level AA unless the governing standard is stricter. This is a design-time gate, not a conformance claim: implementation must still be tested with keyboard-only use, screen readers, automated tooling, contrast/zoom/reflow checks, and representative users when required.

### 5. Generate and validate

From the skill directory, run:

```bash
python3 scripts/arch_studio.py validate <project>.arch.json
python3 scripts/arch_studio.py build <project>.arch.json --out <output-directory> --strict
```

`build --strict` must exit zero for final delivery. It produces a multi-page `.drawio`, static clickable `review.html`, audit and traceability reports, architecture decisions, threat/risk summary, and a SHA-256 receipt. When `ui_spec` is active, it also produces `ui-specification.md`, `ui-component-matrix.csv`, `ui-acceptance-plan.md`, and `design-tokens.json`. Structural failures always block. Governance, Kubernetes, or UI-quality blockers can pass only through a current, explicitly owned waiver with rationale and expiry when the finding allows waivers.

Repair diagnostics at their source in the canonical model. After three consecutive rounds without reducing blocking findings, stop and report the exact unresolved findings instead of weakening the gate.

### 6. Conduct visual specification review

Read [references/interactive-review.md](references/interactive-review.md). The generated `review.html` is the primary design-review surface. Reviewers can select architecture components, connections, views, decisions, risks, findings, UI screens, regions, actions, states, flow steps, and UI components; accept, reject, or request changes; attach comments; and export a structured `review-decisions.json` or a Claude-ready change prompt.

For offline review, open `review.html` directly. For persisted decisions and optional chat:

```bash
python3 scripts/arch_studio.py serve <project>.arch.json --out <output-directory> --open
```

The chat bridge is disabled unless `--claude-bridge` is supplied. To continue a specific Claude Code conversation, also supply `--claude-session <session-id-or-name>`. The bridge binds to loopback, restricts Claude to structured output with no tools, validates any returned model, writes atomically, keeps a backup, and regenerates the artifacts. Never use a permission-bypass flag.

### 7. Revise and compare

Apply accepted review changes to the canonical JSON, preserve unrelated IDs and placements, rerun strict build, and record superseded decisions. To compare two versions:

```bash
python3 scripts/arch_studio.py diff before.arch.json after.arch.json --out architecture-delta.md
```

Do not treat a visual move as an architecture change unless semantics changed. Report added, removed, and materially changed components, connections, requirements, decisions, risks, and views.

## Delivery contract

Return:

- the canonical `<project>.arch.json`;
- the multi-page `<project>.drawio`;
- `review.html`;
- `governance-report.md` and `governance-report.json`;
- `traceability.csv`, `architecture-decisions.md`, `risk-and-threat-summary.md`, and `build-receipt.json`;
- when UI is active, `ui-specification.md`, `ui-component-matrix.csv`, `ui-acceptance-plan.md`, and `design-tokens.json`;
- the strict-gate result, remaining assumptions/questions, and every active waiver.

Never claim that a diagram proves deployed reality. State whether the model is user-confirmed, repository-evidenced, inferred, or proposed.

## Additional resources

- [references/dev-loop.md](references/dev-loop.md): `/dev-loop` spec-stage review in Cursor chat.
- [references/installation.md](references/installation.md): install and first-run guidance.
- [references/architecture-model.md](references/architecture-model.md): canonical fields, stable IDs, evidence, views, and placements.
- [references/discovery-grill.md](references/discovery-grill.md): `design-tree-interview` prompt contract and completeness gate.
- [references/diagram-pack.md](references/diagram-pack.md): view catalog and pack selection.
- [references/design-quality.md](references/design-quality.md): system-design and implementation review heuristics.
- [references/azure-governance.md](references/azure-governance.md): Azure landing-zone and Well-Architected gate.
- [references/kubernetes-review.md](references/kubernetes-review.md): Kubernetes/AKS production gate.
- [references/interactive-review.md](references/interactive-review.md): review decisions and Claude bridge.
- [references/ui-specification.md](references/ui-specification.md): responsive UI model, state coverage, accessibility, backend bindings, and implementation handoff.
