# UI specification and implementation handoff

Read this reference when a request includes a user interface, portal, dashboard, admin surface, mobile/web client, workflow, or reviewable product experience. UI work remains inside the canonical `*.arch.json`; it is not a disconnected mockup.

## Evidence before invention

Inspect the existing frontend before proposing a design:

- routes, layouts, feature folders, component library, Storybook, tokens, themes, icons, fonts, and content conventions;
- authentication, route guards, role/claim checks, feature flags, form validation, API clients, query/cache conventions, and error handling;
- unit/component/accessibility/integration/E2E/visual-regression tests and their selectors;
- analytics events, consent/privacy handling, performance budgets, browser/device support, localization, and observability.

Record repository evidence and confidence. Reuse the established design system and interaction conventions unless a requirement justifies a change. If none exists, Fluent 2 is the Azure-aligned default, but record it as a proposed decision rather than an observed fact.

## UI discovery (`design-tree-interview`)

Add only unanswered, decision-relevant topics to the normal discovery loop:

1. users/personas, roles/claims, primary jobs, frequency, environment, and access needs;
2. supported platforms, devices, browsers, viewport ranges, input modes, locales, time zones, and connectivity constraints;
3. information architecture, routes, entry/deep-link behavior, back/refresh behavior, unsaved work, session expiry, and cross-device continuity;
4. task success, abandonment, validation, confirmation, destructive actions, bulk actions, permissions, audit needs, and support/recovery paths;
5. content source/owner, empty/error/help copy, terminology, formatting, localization, and regulated disclosures;
6. data shown/entered, classification, minimization, masking, authorization, retention, analytics properties, consent, and redaction;
7. existing design system, brand/tokens, density, dark/high-contrast modes, responsive behavior, and accessibility target;
8. frontend stack, state/data-fetching/validation patterns, API contracts, feature flags, telemetry, rollout, and testing ownership.

Do not ask for colors or visual polish before the user goal, content, state machine, authorization, and data contracts are known.

## Canonical `ui_spec`

Use [../assets/architecture.schema.json](../assets/architecture.schema.json). `ui_spec` is optional for architecture-only work and required whenever UI-specific views are generated.

### Design system and tokens

Record the system name, source, reuse policy, and semantic tokens. Prefer semantic names such as `color.text.primary`, `color.status.danger`, `space.control.gap`, `type.body.size`, `radius.control`, and `focus.ring`. Do not encode a screen as isolated hex values. The generator exports `design-tokens.json` and explicitly disables motion.

### Personas and flows

Personas are role/access-need summaries, not fictional biographies. Each flow has one user goal, entry screens, preconditions, ordered screen steps, observable outcomes, exception paths, and requirement references. Split unrelated goals into separate flows.

### Screen contract

Every screen records:

- stable ID, route, purpose, permitted roles, data classification, requirements, flows, and evidence;
- semantic regions in reading/focus order, each backed by a reusable UI component;
- visible actions with label, type, authorization, keyboard behavior, target screen or binding, and confirmation/undo for destructive work;
- screen states with trigger, content, available actions, focus target, and screen-reader announcement;
- a layout for every supported breakpoint, with all visible regions placed and non-overlapping.

Required state coverage is contextual:

| Situation | Required states |
| --- | --- |
| Every screen | default |
| Data-bound screen | loading, empty, error |
| Restricted screen | permission-denied |
| Submission or mutation | success and validation/error behavior |
| Intermittent connectivity | offline and reconnect/degraded behavior |
| Destructive work | destructive-confirmation plus recovery/undo where possible |

Do not use a spinner without surrounding content behavior. State whether prior data remains, actions are disabled, cancellation is possible, retry is safe, focus moves, and a live region announces the change.

### UI-to-system bindings

Every data-bound region links to:

- the UI screen and region;
- the architecture component that serves it;
- the architecture relationship when one represents the transport;
- operation/transport, request and response contract, authorization, loading behavior, error/retry behavior, and requirements.

This closes the gap between “the page calls the API” and an implementable contract. Never invent an endpoint path or payload from a diagram; use repository/OpenAPI evidence or mark a proposed contract explicitly.

### Navigation, analytics, and privacy

Navigation records source, target, trigger, conditions, authorization/dirty-state guards, back behavior, and requirements. Specify deep links, refresh, session expiry, forbidden routes, and return destinations when material.

Analytics events use stable names and list only approved properties. Exclude secrets, free-form sensitive content, tokens, full payloads, and unapproved personal data. Record consent and retention expectations in the privacy field.

## Accessibility gate

Default target: WCAG 2.2 Level AA, or a stricter governing standard. The model must describe:

- native semantics first; ARIA only where needed; accessible name, role, state, value, description, and error association;
- complete keyboard operation, logical focus order, visible focus, focus entry/restoration for dialogs and errors, and no keyboard traps;
- headings, landmarks, page title, status/live announcements, table/form semantics, alt text, and reading order;
- text and non-text contrast, target size/spacing, 200% zoom, 320 CSS-pixel reflow, text spacing, orientation, and high-contrast behavior;
- no animation; static state changes remain understandable and do not depend on motion;
- automated checks plus manual keyboard and screen-reader testing at supported breakpoints.

Do not claim conformance from the specification or generated wireframes. Only tested implementation evidence can support that claim.

## Technical implementation handoff

Record the chosen frontend stack, design-system package/version policy, state management, data-fetching/cache/query-key pattern, form/schema validation, feature-flag strategy, telemetry/error boundaries, and test pyramid. Prefer repository-native patterns over introducing new dependencies.

Generated handoff artifacts are:

- draw.io `user-flow`, `ui-wireframe`, and `ui-state-map` pages;
- interactive review objects for screens, regions, actions, states, flow steps, and components;
- `ui-specification.md` for the full readable contract;
- `ui-component-matrix.csv` for component ownership and reuse;
- `ui-acceptance-plan.md` for journey, state, binding, responsive, and accessibility tests;
- `design-tokens.json` for implementation-ready semantic tokens.

## Review closure

Do not approve UI scope until every required screen state and breakpoint is covered, visible actions have permission and keyboard behavior, data bindings reach architecture contracts, destructive paths are recoverable, analytics is privacy-reviewed, accessibility tests are owned, and rejected/modify decisions in `review.html` are resolved or explicitly deferred.
