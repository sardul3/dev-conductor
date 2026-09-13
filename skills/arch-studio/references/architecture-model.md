# Canonical architecture model

The canonical `*.arch.json` is the source of truth. Generated files are disposable views of it.

## Identity and lifecycle

- `schema_version` is currently `1.0`.
- `project.id` and every entity ID use lowercase kebab case and remain stable across revisions.
- Increment `project.version` when a reviewed semantic change is accepted.
- Use `draft`, `in-review`, `approved`, `implemented`, or `retired` for project status.
- Never reuse an ID for a different concept.

## Evidence and confidence

Facts may include:

```json
{
  "source": "repository|document|user|runtime|inference|proposal",
  "reference": "relative/path.ext:10-24",
  "commit": "optional immutable revision",
  "confidence": "high|medium|low",
  "note": "what this evidence supports"
}
```

Use `runtime` only for directly observed runtime evidence. A repository declaration is not proof that production matches it. `proposal` is the default for target-state components not yet implemented.

## Traceability

- Requirements use IDs such as `req-availability` or `req-order-created-event`.
- Components and relationships list the requirements they satisfy.
- Controls list the requirements and risks they address.
- Views list the requirements or decisions they explain when useful.
- A strict build warns on orphan requirements and blocks invalid references.
- UI screens, flows, reusable components, bindings, navigation, and UI views list the requirements they implement or explain.

## Components

Every component needs `id`, `name`, `kind`, `description`, `technology`, `owner`, `criticality`, `data_classification`, `lifecycle`, `requirements`, `controls`, and `evidence`.

Include implementation details that affect review: region, resource group, namespace, SKU, scaling, persistence, public exposure, and dependencies as applicable.

`kind` is semantic: `actor`, `external-system`, `client`, `gateway`, `service`, `function`, `worker`, `message-broker`, `database`, `cache`, `storage`, `identity`, `security`, `observability`, `pipeline`, `repository`, `kubernetes`, `network`, or `generic`.

Use `azure_service` IDs from `assets/azure-icons.json` when a real Azure service is selected. Omit it for a generic or undecided service.

## Relationships

Every relationship needs stable `id`, `from`, `to`, `label`, and `direction`. Add `protocol`, `port`, `auth`, `mode`, data names/classifications, encryption, timeout, retry, idempotency, ordering, failure behavior, requirements, controls, and evidence when applicable.

Do not write vague labels such as `calls`, `uses`, or `data`. Prefer `Create order · HTTPS/443 · OIDC · sync` or `OrderCreated v2 · AMQP/TLS · async`.

## Views and placement

Each view is one draw.io page and one review tab. Required fields are `id`, `title`, `type`, `purpose`, `width`, `height`, `nodes`, and `legend`.

Graph views reference top-level components and relationships:

```json
{
  "id": "deployment",
  "title": "Production deployment and network",
  "type": "deployment",
  "purpose": "Show Azure placement and network trust boundaries",
  "width": 1600,
  "height": 900,
  "boundaries": [
    {"id": "azure", "label": "Azure tenant", "kind": "cloud", "x": 260, "y": 60, "w": 1260, "h": 760}
  ],
  "nodes": [
    {"component": "api", "x": 620, "y": 280, "w": 180, "h": 100, "boundary": "aks-namespace"}
  ],
  "edges": ["rel-client-api"],
  "legend": {"mode": "auto", "x": 1240, "y": 680}
}
```

Coordinates are draw.io canvas units. Boundaries are declared before their children and use `parent` for nesting. A node's `boundary` is optional. Keep at least 24 units between peer nodes and 32 units from a containing boundary edge. Use left-to-right primary flow unless domain convention requires otherwise.

Sequence views use `participants` and ordered `interactions`. A participant is a component ID. Each interaction has `from`, `to`, `label`, `kind` (`sync`, `async`, `return`), and optional `note`.

UI views use `ui_spec`:

- `user-flow` sets `flow` to a `ui_spec.flows` ID;
- `ui-wireframe` sets `screen`, `breakpoint`, and optionally `state`;
- `ui-state-map` sets `screen`.

Keep `nodes: []` for generated UI views. Screen-region geometry lives in `ui_spec.screens[].layouts[]` so the same responsive contract drives draw.io and HTML review output. Read [ui-specification.md](ui-specification.md) for the complete UI model.

## Legend

Use `{"mode":"auto"}` by default. The renderer derives entries from component kinds, connection modes, and boundary kinds. Use authored `entries` only when a symbol has project-specific meaning.

## Decisions, risks, questions, and waivers

- Decisions include status, context, choice, rationale, alternatives, consequences, owner, date, and affected IDs.
- Risks include likelihood, impact, exposure, mitigation, owner, status, and affected IDs.
- Open questions include owner, blocking flag, due/revisit date, and consequence.
- Waivers include the exact finding code, scope, rationale, compensating controls, approver or owner, and ISO date expiry. Expired or incomplete waivers never pass a gate.

## Revision discipline

When applying review feedback, preserve unrelated architecture and UI IDs and positions, change the smallest coherent set of fields, update ADRs, risks, bindings, states, acceptance coverage, and traceability, rerun strict build, and use `diff` to show the semantic change.
