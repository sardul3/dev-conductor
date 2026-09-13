# Diagram pack selection

One canonical model may produce several draw.io pages. Choose views by the decisions they enable, not by a fixed page count.

## Focused pack

Use when the user explicitly wants one narrow diagram. Include the requested view plus any trust boundary or deployment context needed to keep it truthful.

## Standard Integration Pack (default)

Use for adding system X to an existing system, a new API/event integration, or a production feature spanning services.

1. System context — actors, external systems, system boundary, ownership.
2. Logical services/containers — responsibilities, stores, brokers, primary flows.
3. Azure deployment/network — landing zone, regions, subscriptions, VNets/subnets, ingress/egress, private endpoints.
4. Security/identity/trust — identities, authorization, secrets, trust crossings, security controls.
5. Data flow/classification — producers, transformations, stores, retention/residency, consumers.
6. Critical-path sequence — success path plus the most important failure or compensation path.
7. Runtime — AKS namespaces/workloads/policies or the selected compute runtime.
8. Delivery and operations — CI/CD or GitOps, observability, backup, recovery, ownership handoffs.

## Comprehensive Enterprise Pack

Use when the user asks for all diagrams, an architecture review board package, or implementation handoff. Add relevant views from the catalog and include an executive overview page.

| Type | Decision enabled | Required content |
| --- | --- | --- |
| `system-context` | Scope and external dependency agreement | Actors, systems, boundary, purpose, ownership |
| `container` | Responsibility and technology split | Services, stores, brokers, APIs/events, owners |
| `component` | Internal design review | Modules, ports/adapters, dependencies, test seams |
| `deployment` | Cloud/platform placement | Environments, regions/zones, subscriptions, resource groups, compute/data |
| `network` | Connectivity review | VNets/subnets, routes, firewall, DNS, ingress/egress, private endpoints |
| `security` | Threat/control review | Identities, trust zones, privileges, secrets, controls, audit paths |
| `data-flow` | Data governance and lineage | Classification, transformations, retention, residency, stores, consumers |
| `sequence` | Runtime contract review | Ordered calls/events, auth, timeout, retry, failure, compensation |
| `kubernetes` | Platform and workload review | Cluster, pools, namespaces, ingress, policy, scaling, identity, secrets |
| `ci-cd` | Delivery control review | Build, scan, sign, promote, approve, deploy, verify, rollback |
| `observability` | Operability review | Telemetry sources, collectors, stores, dashboards, alerts, SLO ownership |
| `resilience` | Failure and DR review | Failure domains, degradation, queues, backup, failover, restore, RTO/RPO |
| `migration` | Cutover agreement | Current/transition/target state, data migration, coexistence, rollback |
| `lifecycle` | State-machine agreement | States, events, guards, retries, terminal outcomes |
| `executive` | Nontechnical approval | Outcome, boundary, major risk, cost/operating implications, decision asks |
| `user-flow` | Product journey agreement | Persona, goal, ordered screens/actions, outcomes, exception paths |
| `ui-wireframe` | Responsive screen contract | Route, regions, component reuse, actions, bindings, state, breakpoint |
| `ui-state-map` | Complete state/recovery agreement | Triggers, content, actions, focus, announcements, retry/recovery |

## Density and decomposition

- Target 6–14 primary elements per view and one obvious reading path.
- Split a view when more than two abstraction levels or more than three distinct decisions compete.
- Reuse stable components across pages; do not create page-specific aliases for the same service.
- Put detailed configuration in component metadata and reports, not tiny diagram text.
- Show one success path and only decision-relevant exceptions. Use a separate sequence or resilience page for detailed failures.
- Keep product names and protocols exact. A legend explains notation, not architecture.
