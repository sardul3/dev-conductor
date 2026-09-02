# Risk and threat summary: Retail order integration

> This register is design evidence. Validate controls against implementation and authorized runtime evidence before production approval.

| ID | Category | Exposure | Risk | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `risk-cluster-misconfiguration` | kubernetes security | high | An AKS workload bypasses isolation or production safety defaults | Restricted PSS, admission policy, default-deny network policy, non-root baseline, quotas, GitOps, and policy evidence. | Azure Platform Team | mitigating |
| `risk-credential-misuse` | identity | high | A shared or long-lived credential grants excessive Azure access | Workload identity, per-service accounts, least-privilege roles, Key Vault, PIM, rotation, and access review. | Security Architecture | mitigating |
| `risk-data-exposure` | data protection | high | Confidential order data is exposed through a public or over-permissive data path | Private endpoints, Private DNS, encryption, scoped identities, audited access, classification, retention, and policy controls. | Data Governance | mitigating |
| `risk-duplicate-event` | reliability | high | A retried event causes duplicate fulfillment action | Stable event ID, idempotent consumer record, bounded redelivery, and audited replay. | Fulfillment Team | mitigating |
| `risk-event-loss` | reliability | high | An accepted order is never published for fulfillment | Atomic outbox, backlog-age alert, durable retry, reconciliation, and owned recovery runbook. | Retail Ordering Team | mitigating |
| `risk-public-abuse` | security | high | Automated abuse or volumetric traffic reaches the order API | Front Door Premium WAF, bot and rate rules, DDoS decision, authentication, origin restriction, load shedding, and alerting. | Security Architecture | mitigating |
| `risk-region-outage` | resilience | high | A regional outage exceeds the assumed availability objective | Zonal HA, tested restore and GitOps bootstrap, recovery runbook, business acceptance of the regional tradeoff, and a trigger for multi-region reassessment. | Architecture Review Board | accepted |
| `risk-supply-chain` | supply chain | high | A vulnerable or untrusted artifact reaches production | Protected source, scanning, SBOM, signed provenance, digest promotion, admission verification, and rollback. | DevSecOps Team | mitigating |
| `risk-undetected-failure` | operations | high | Order-path degradation is not detected before material customer impact | Edge SLIs, dependency and business telemetry, error-budget alerts, synthetic checks, owned runbooks, and game days. | SRE Team | mitigating |

## Security control coverage

- **ctl-edge-protection · Edge protection** — Front Door Premium WAF, bot and rate rules, DDoS decision, TLS policy, and private APIM origin. (owner: Azure Platform Team; status: proposed)
- **ctl-workload-identity · Workload identity and secrets** — Entra Workload ID, managed identities, Key Vault CSI, least-privilege RBAC, rotation, and access logging. (owner: Security Architecture; status: proposed)
- **ctl-private-data · Private data plane** — Private endpoints, Private DNS, firewall egress, encryption, database RBAC, and audited access. (owner: Azure Platform Team; status: proposed)
- **ctl-k8s-baseline · Restricted AKS workload baseline** — Restricted PSS, non-root, seccomp, no privilege escalation, dropped capabilities, requests/limits, probes, PDB, topology spread, HPA, and default-deny policy. (owner: Azure Platform Team; status: proposed)
- **ctl-supply-chain · Software supply-chain integrity** — Dependency and secret scan, image scan, SBOM, signed provenance, digest promotion, admission verification, and health-gated GitOps rollout. (owner: DevSecOps Team; status: proposed)

## Threat-model prompts for implementation review

- Entry points and trust crossings: validate authentication, authorization, abuse controls, TLS, rate limiting, and evidence.
- Sensitive data: validate minimization, classification, access logging, retention, deletion, backup isolation, and key ownership.
- Workload and platform identities: validate least privilege, token scope/lifetime, rotation, privileged escalation paths, and break-glass monitoring.
- Supply chain: validate dependency and image provenance, SBOM, scanning, signing, promotion, admission, and rollback.
- Failure and recovery: validate timeout, retry, idempotency, backpressure, DLQ/replay, failover, restore, and incident runbooks.
