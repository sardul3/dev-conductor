# Kubernetes and AKS production review

Apply only when Kubernetes is selected. First record why Kubernetes is preferable to App Service, Container Apps, Functions, or another simpler runtime.

## Cluster and platform

- Supported Kubernetes and node OS versions, upgrade channel, maintenance windows, surge capacity, and rollback or mitigation are explicit.
- Production control plane is private unless a documented requirement justifies public access with restricted API ranges.
- System and user node pools are separated when needed; pools span availability zones when SLOs justify it; autoscaler bounds and quotas are explicit.
- Entra integration, Azure RBAC or Kubernetes RBAC boundaries, PIM, break-glass access, and audit logs are explicit.
- Microsoft Entra Workload ID is used for Azure access. Pod-managed long-lived credentials are blocked.
- Azure Policy or admission controls and Defender for Containers or approved equivalents are explicit.

## Tenancy and namespaces

- Cluster tenancy and isolation model are intentional. Do not place hostile or materially different trust levels in one cluster without stronger isolation.
- Namespace ownership, RBAC, service accounts, quotas, limit ranges, network policy, Pod Security Admission labels, and secret access are defined.
- Default-deny ingress and egress policies exist, with explicit DNS and required dependency allowances.

## Workload baseline

For every production workload, require or explain non-applicability:

- at least two replicas for availability-sensitive stateless services;
- readiness, liveness, and startup probes with distinct purposes;
- CPU and memory requests and limits based on measurement;
- HPA or KEDA signal and bounds when elasticity is required;
- PodDisruptionBudget and topology spread or anti-affinity;
- graceful termination, connection draining, and termination budget;
- immutable image pinned by digest; vulnerability scanning, provenance or signing, and SBOM;
- `runAsNonRoot`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem` when compatible, `seccompProfile: RuntimeDefault`, and dropped capabilities;
- no privileged, host namespace, or hostPath use unless explicitly approved;
- workload identity and external secret delivery from Key Vault; no secrets in Git or plain environment configuration;
- retry, idempotency, and backpressure behavior that matches Kubernetes restarts and rescheduling.

## Networking and state

- Ingress path, TLS termination, certificate lifecycle, WAF or rate limiting, source IP needs, and health checks are explicit.
- Internal and external load balancer intent is clear. Services are not public by accidental type or annotation.
- Network policy implementation and limits are understood. Egress goes through the selected control plane and preserves required DNS and service endpoints.
- Prefer managed Azure data services unless Kubernetes ownership is justified.
- Storage class, zone binding, access mode, encryption, snapshots, backup, restore, replication, rescheduling, and upgrade behavior are explicit. A PVC is not a backup.

## Delivery, policy, and operations

- GitOps or controlled CI/CD owns declarative manifests. Direct production changes are exceptional and audited.
- Build uses trusted bases, locked dependencies, secret scanning, SAST, image scanning, SBOM, signing, admission verification, and provenance.
- Promotion uses immutable artifacts; rollout strategy, automated health verification, rollback, schema compatibility, and feature flags are addressed.
- Metrics, logs, traces, Kubernetes events, control-plane logs, and audit logs are collected with bounded retention.
- SLOs, alerts, dashboards, and runbooks cover user impact, saturation, pending pods, restarts, throttling, OOM, queue backlog, certificates, DNS, and node or cluster health.
- Load, disruption, upgrade, node-drain, zone-failure, dependency-failure, backup, and restore tests are planned.

## Gate semantics

The checker can confirm that the model states these controls; it cannot prove manifests or a live cluster implement them. Cite repository paths, policy results, or authorized runtime evidence separately and retain timestamp and scope.

