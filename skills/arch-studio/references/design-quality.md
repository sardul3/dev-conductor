# System design and implementation quality

Use this reference while selecting and reviewing the target design. It is a decision aid, not a reason to add infrastructure.

## Simplicity and boundaries

- Align components with business capabilities, ownership, independent change, scaling, data authority, or trust boundaries.
- Prefer a modular monolith or managed platform when independent deployment and scaling are not needed.
- Do not share a writable database across independently owned services without recording the coupling and migration plan.
- Make the system of record and write authority explicit for every important entity.

## Integration contracts

- Choose synchronous calls for immediate results and bounded latency; choose asynchronous messaging for decoupling, buffering, fan-out, or long-running work.
- Define contract ownership, versioning, compatibility, validation, rate limits, pagination, and deprecation.
- For asynchronous paths, define delivery semantics, ordering scope, idempotency key, deduplication, replay, poison-message handling, DLQ ownership, and reconciliation.
- For synchronous paths, define timeout budget, retry policy, idempotency, circuit breaking, fallback/degradation, and correlation IDs.
- Avoid dual writes. Use a transactional outbox, change data capture, saga/compensation, or another explicitly justified consistency pattern.

## Data

- Minimize movement and retention of sensitive data. Classify every store and material flow.
- Define encryption, keys, backup, restore testing, retention, deletion, legal hold, residency, lineage, and access logging.
- Match store type to access patterns and consistency requirements. Record the tradeoff, capacity model, partition key, indexing, and growth plan.
- Separate operational, analytical, and audit workloads when their access and retention characteristics differ.

## Reliability and performance

- Start from user-facing SLOs and dependency budgets. Show failure domains and single points of failure.
- Use availability zones or regions only when SLO/RTO/RPO justify their cost and complexity.
- Define load shedding, backpressure, queue depth alarms, capacity headroom, autoscaling signals, and dependency saturation behavior.
- Validate performance with representative payloads, peak concurrency, degraded dependencies, and recovery after backlog.
- Document backup success separately from restore proof.

## Security

- Use zero-trust principles: verify explicitly, least privilege, assume breach, minimize trust crossings.
- Prefer workload identity and short-lived credentials; avoid long-lived secrets and shared identities.
- Make public exposure exceptional and explicit. Use private endpoints and controlled egress where appropriate.
- Model threats at entry points, trust crossings, sensitive operations, data stores, admin paths, and supply-chain boundaries.
- Include prevention, detection, response, evidence, and owner for material controls.

## Delivery and operations

- Infrastructure, policy, configuration, and application delivery should be reproducible and peer reviewed.
- Define promotion, approvals, provenance, scanning, signing, rollout, health verification, rollback, and audit history.
- Emit logs, metrics, and traces with correlation. Define SLOs, alerts tied to user impact, dashboard owners, runbooks, and escalation.
- Design day-2 operations: patching, upgrades, certificate rotation, schema evolution, capacity, cost, incident response, and decommissioning.

## Review smells

Treat these as prompts for clarification:

- Kubernetes or microservices chosen without workload or team justification.
- Multi-region drawn without data consistency and failover operations.
- A queue shown without retry, DLQ, replay, and ownership.
- Cache shown without invalidation, TTL, stampede, and source-of-truth behavior.
- Public endpoint shown without WAF, DDoS, rate limiting, and authentication.
- Database shown without backup/restore, classification, private access, and ownership.
- Cross-boundary arrow shown without protocol, auth, encryption, and data.
- “Monitoring” shown without telemetry sources, SLOs, alerts, retention, and owner.
- “CI/CD” shown without provenance, security gates, promotion, verification, and rollback.
- An ideal target state that omits migration, coexistence, and decommissioning.

