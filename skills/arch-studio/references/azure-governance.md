# Azure governance and architecture gate

Apply this gate to Azure target-state designs. It aligns the review with Azure Well-Architected principles, Cloud Adoption Framework landing-zone design areas, Microsoft Cloud Security Benchmark concepts, and the AKS baseline when AKS is used. It does not replace tenant-specific Azure Policy or an organization's architecture review board.

## Gate levels and waivers

- `blocker`: unsafe or materially incomplete for production; strict build fails.
- `warning`: should be resolved or consciously accepted before implementation.
- `info`: improvement or implementation note.

A waiver may suppress an eligible blocker only when it names the finding code and scope, has rationale, compensating controls, owner or approver, and a future expiry date. Identity, secrets, encryption, unknown public exposure, and invalid evidence findings are not automatically waiverable.

## Landing zone and organization

- Application landing zone, management-group placement, subscription/environment strategy, resource groups, ownership, and separation of duties are explicit.
- Azure Policy assignment and exemption scopes are explicit; exemptions have owners and expiry.
- Required tags include owner, application/workload, environment, cost center, data classification, and criticality.
- Resource locks, budgets, cost alerts, Defender plans, diagnostic settings, and activity-log retention are addressed.
- Naming, region allowlist, SKU restrictions, and data-residency constraints are recorded.

## Identity and access

- Human identity uses Microsoft Entra ID, organizational MFA/Conditional Access policy, least-privilege Azure RBAC, PIM/JIT for privileged roles, break-glass controls, and access review.
- Workloads use managed identity or Microsoft Entra Workload ID. Shared accounts and embedded credentials are blocked.
- Key Vault or an approved secret store owns secret, key, and certificate lifecycle, rotation, access logging, soft delete, and purge protection.
- Control-plane, data-plane, CI/CD, and emergency access are separated and auditable.

## Network and exposure

- Network topology and ownership are explicit: hub-spoke or Virtual WAN, address space, peering, DNS, routing, and shared services.
- Public ingress is explicit and protected by an appropriate edge, WAF, TLS policy, rate limiting, DDoS controls, and origin restriction.
- Private Link or private endpoints are used for sensitive PaaS data services unless a documented constraint prevents it.
- Egress is intentional, observable, and controlled; DNS and route dependencies are shown.
- Hybrid or partner connectivity includes encryption, redundancy, routing ownership, allowlists, and failure behavior.
- NSGs, ASGs, and firewalls express least privilege. Do not treat a VNet as an authorization control.

## Data protection

- Classification, residency, retention, deletion, audit, and ownership are explicit.
- Encryption in transit and at rest is explicit; CMK need and key ownership are decided.
- Backups are isolated as needed; restore is tested against RTO/RPO; cross-region replication matches consistency and residency constraints.
- Data stores disable unnecessary public access, expose diagnostic logs, and have lifecycle, patching, and HA responsibilities.

## Reliability and performance

- Availability SLO, dependency budgets, capacity, zones, region strategy, autoscaling, and failure domains are explicit.
- Multi-region is justified by RTO/RPO/SLO and includes traffic management, data failover, split-brain prevention, runbook, and test cadence.
- Timeouts, retries, circuit breaking, load shedding, backpressure, idempotency, and degraded modes are defined where relevant.
- Quotas and limits for selected services are checked before implementation.

## Operational excellence and delivery

- Infrastructure and policy are code-reviewed; environment drift and policy compliance are monitored.
- CI/CD validates code, IaC, dependencies, secrets, containers, SBOM/provenance, policy, deployment health, and rollback.
- Azure Monitor, Log Analytics, Application Insights, or an approved stack provides logs, metrics, traces, dashboards, alerts, and retention.
- SLOs, alert ownership, incident runbooks, on-call path, backup/restore drills, patching, certificate rotation, and cost reviews are explicit.

## Cost and sustainability

- Compute and data SKUs are assumptions or decisions, not invented facts.
- Autoscaling, right-sizing, reservations or savings plans where appropriate, storage lifecycle, log retention, and nonproduction shutdown are considered.
- Cost ownership, budgets, unit-cost measure, anomaly response, and regular review are defined.
- Avoid always-on high-complexity services when a managed or serverless option meets the requirements.

## Evidence boundary

The generated gate is a design-time assessment of the canonical model. It does not query Azure resources or prove deployed compliance. If live validation is required, separately obtain authorized Azure Resource Graph, Policy, Defender, network, identity, and configuration evidence with timestamps and scope.

