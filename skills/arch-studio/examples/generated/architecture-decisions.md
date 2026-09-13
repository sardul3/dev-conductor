# Architecture decisions: Retail order integration

## dec-azure-aks: Use the existing enterprise AKS platform

- Status: **PROPOSED**
- Owner: Architecture Review Board
- Date: 2026-09-02
- Affected: `order-api`, `outbox-worker`, `aks-runtime`

### Context

The organization already operates an AKS application platform and adjacent retail services share its policy, GitOps, and support model.

### Decision

Deploy the order API and outbox worker into a private AKS cluster under an owned production namespace.

### Rationale

Reuses established platform capability and avoids a second operating model for the same team.

### Alternatives considered

- Azure Container Apps
- Azure App Service
- Azure Functions

### Consequences

- Platform team remains accountable for cluster lifecycle.
- Application team must meet the restricted workload baseline.
- A simpler managed runtime should be reconsidered if platform reuse is no longer true.

## dec-transactional-outbox: Use a transactional outbox for event publication

- Status: **PROPOSED**
- Owner: Retail Ordering Team
- Date: 2026-09-02
- Affected: `order-api`, `order-db`, `outbox-worker`, `service-bus`, `rel-api-db`, `rel-worker-bus`

### Context

Order acceptance and event publication must not diverge, and distributed transactions are not supported across PostgreSQL and Service Bus.

### Decision

Commit the order and outbox row in one transaction, then publish asynchronously with a stable event ID.

### Rationale

Avoids dual-write loss while preserving durable retry and independent fulfillment processing.

### Alternatives considered

- Synchronous fulfillment call
- Direct database-to-broker dual write
- Change data capture

### Consequences

- The worker and outbox backlog require operational ownership.
- Consumers must be idempotent.
- Event publication is eventually consistent after order acceptance.

## dec-service-bus: Use Service Bus Premium for the order event

- Status: **PROPOSED**
- Owner: Integration Platform Team
- Date: 2026-09-02
- Affected: `service-bus`, `service-bus-dlq`, `rel-worker-bus`, `rel-bus-fulfillment`

### Context

The integration needs durable delivery, bounded redelivery, dead-lettering, private connectivity, and enterprise ownership.

### Decision

Publish OrderCreated v2 to a Service Bus Premium topic with an owned fulfillment subscription and DLQ.

### Rationale

Meets the enterprise integration requirement without operating a broker on AKS.

### Alternatives considered

- Event Grid
- Event Hubs
- Kafka on a managed platform
- Synchronous API

### Consequences

- Throughput and messaging-unit capacity must be load tested.
- Replay and DLQ runbooks are required.
- Event contract versioning is part of the implementation.

## dec-private-data-plane: Keep confidential PaaS services private

- Status: **PROPOSED**
- Owner: Security Architecture
- Date: 2026-09-02
- Affected: `order-db`, `service-bus`, `key-vault`, `container-registry`, `azure-deployment-network`, `security-trust`

### Context

Order data is confidential and public data-plane exposure is unnecessary.

### Decision

Use private endpoints, Private DNS, and controlled egress for PostgreSQL, Service Bus, Key Vault, and ACR.

### Rationale

Reduces exposure and aligns with the application landing-zone network model.

### Alternatives considered

- Public endpoints with IP allowlists
- Service endpoints where supported

### Consequences

- DNS and network dependencies become production-critical.
- Platform team owns endpoint, route, and firewall lifecycle.
- Troubleshooting requires cross-team telemetry.

## dec-workload-identity: Use federated workload identity

- Status: **PROPOSED**
- Owner: Security Architecture
- Date: 2026-09-02
- Affected: `order-api`, `outbox-worker`, `entra-id`, `key-vault`, `ctl-workload-identity`

### Context

Long-lived credentials in workload configuration create rotation and compromise risk.

### Decision

Use Entra Workload ID and managed identities for Azure resource access.

### Rationale

Provides short-lived tokens, per-workload scope, and auditable access without stored cloud credentials.

### Alternatives considered

- Kubernetes secrets containing client secrets
- Shared managed identity

### Consequences

- Federated credentials and service accounts must be managed as code.
- Each workload needs explicit least-privilege role assignments.

## dec-single-region-zonal: Use one region with zonal high availability for initial production

- Status: **PROPOSED**
- Owner: Architecture Review Board
- Date: 2026-09-02
- Affected: `order-db`, `service-bus`, `order-api`, `resilience-recovery`, `risk-region-outage`

### Context

The assumed 99.9% SLO and 60-minute RTO do not currently justify active multi-region complexity.

### Decision

Use zone-aware AKS, API Management capacity, PostgreSQL HA, and Service Bus Premium in East US 2 with tested restore.

### Rationale

Meets the assumed objectives with lower operational and data-consistency complexity.

### Alternatives considered

- Active-passive second region
- Active-active multi-region

### Consequences

- A regional outage can exceed the monthly SLO and requires restore or redeployment.
- Business must confirm the SLO and RTO assumption before approval.
- A second region should be added if objectives tighten.

## dec-gitops-supply-chain: Promote signed digests through GitOps

- Status: **PROPOSED**
- Owner: DevSecOps Team
- Date: 2026-09-02
- Affected: `git-repository`, `build-pipeline`, `container-registry`, `flux-gitops`, `delivery-gitops`

### Context

Production deployment needs immutable artifacts, peer-reviewed desired state, provenance, and deterministic rollback.

### Decision

Build once, scan and sign the image, promote its digest through protected environment repositories, and let Flux reconcile it.

### Rationale

Separates artifact production from environment approval and provides an auditable desired state.

### Alternatives considered

- Pipeline directly applies manifests
- Mutable environment tags

### Consequences

- Signing and admission availability are deployment dependencies.
- Emergency change has a documented and audited Git path.
- Rollback is a Git revision and prior signed digest.

## dec-observability-slo: Measure SLOs at the customer edge and correlate dependencies

- Status: **PROPOSED**
- Owner: SRE Team
- Date: 2026-09-02
- Affected: `azure-monitor`, `observability-operations`, `ctl-observability`

### Context

Platform health alone does not show whether customers can place orders.

### Decision

Calculate availability and latency SLIs at Front Door and correlate them with APIM, AKS, PostgreSQL, Service Bus, and business-event telemetry.

### Rationale

Connects alerts and error budgets to the user outcome while retaining dependency diagnosis.

### Alternatives considered

- Infrastructure-only monitoring
- Application logs without distributed correlation

### Consequences

- Telemetry requires redaction and bounded retention.
- SRE and product owners share SLO governance.
- Exporter failure must not block order processing.
