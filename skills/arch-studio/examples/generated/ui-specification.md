# UI specification: Retail order integration

- Status: **IN-REVIEW**
- Platforms: web
- Design system: Fluent 2 reference profile
- Design source: Proposed Azure-aligned default; replace with the repository design system when one exists
- Reuse policy: Use existing product components first, then Fluent-compatible primitives; create a new component only for an unserved semantic contract.

> This is a design and implementation contract. Accessibility claims require testing against the implemented product, not only this specification.

## Personas and access needs

### ui-persona-retail-customer: Authenticated retail customer

- Roles: customer
- Goals: Review the order, Submit it once, Recover safely from a transient failure
- Access needs: Keyboard-only operation, Screen-reader announcements, 200% zoom and 320 CSS-pixel reflow, Clear error recovery without relying on color

## Responsive contract

| Breakpoint | Range | Grid | Gutter |
| --- | --- | --- | --- |
| `ui-compact` · Compact phone and narrow window | 0–767px | 4 columns | 16px |
| `ui-wide` · Tablet landscape and desktop | 768–∞px | 12 columns | 24px |

## User flows

### ui-flow-submit-order: Review and submit an order

- Actor: `ui-persona-retail-customer`
- Goal: Submit one valid order and receive a durable confirmation without duplicate creation.
- Preconditions: Customer has an authenticated session, Cart has at least one available item, A stable checkout idempotency key exists

| Step | Screen | User action | Observable outcome | Alternate |
| --- | --- | --- | --- | --- |
| 1 | `ui-screen-order-entry` | reviews items, quantities, totals, and delivery information | The complete order summary and editable fields are available in logical reading order. | Unavailable items are identified inline and submission remains disabled until resolved. |
| 2 | `ui-screen-order-entry` | activates Submit order once | The action is disabled, the same idempotency key is sent, progress is announced, and duplicate activation is prevented. | A network or service error preserves entered data and offers a retry with the same key. |
| 3 | `ui-screen-order-entry` | reviews the confirmed order ID | A durable confirmation, next step, and navigation to orders are available and announced. | — |

Success: Exactly one order is created, The customer receives an order ID, Submission status is understandable without motion or color alone

Exceptions: Validation error, Permission or session failure, Offline or timeout, Backend rejection with retry-safe correlation ID

## Screen contracts

### ui-screen-order-entry: Review and submit order

- Route: `/checkout/review`
- Purpose: Let an authenticated customer verify the order, correct issues, submit once, and recover without losing work.
- Roles: customer
- Data classification: confidential
- Requirements: `req-order-submit`, `req-ui-order-experience`, `req-latency`, `req-security`, `req-data`

#### Regions and actions

| Region | Landmark/role | Component | Visibility | Actions | Bindings |
| --- | --- | --- | --- | --- | --- |
| `ui-region-header` · Checkout header | banner | Checkout page header | Always after route authorization | View orders [customer] | — |
| `ui-region-summary` · Order summary | complementary | Order summary | Default, error, and success states when authorized data is available | — | `ui-binding-submit-order` |
| `ui-region-form` · Order review form | main | Order review form | Default and error states for an authorized customer | Submit order [customer with valid order] | `ui-binding-submit-order` |
| `ui-region-status` · Submission status | status | Order status panel | Non-default state or validation summary is present | Retry submission [customer with retained idempotency key] | `ui-binding-submit-order` |

#### States

| State | Trigger | Content | Actions | Focus | Announcement |
| --- | --- | --- | --- | --- | --- |
| `ui-state-default` · default | Order data and authorization are available | Review order details and submit when the summary is correct. | `ui-action-submit-order`, `ui-action-orders` | Page heading on initial navigation; preserve current focus after inline edits | Order review loaded |
| `ui-state-loading` · loading | Order query is pending with no usable cached result | Loading the order summary; controls are not exposed until labels and values are available. | — | Keep focus on the initiating navigation target | Loading order review |
| `ui-state-empty` · empty | The order contains no purchasable items | Your cart is empty. Add an item before checkout. | `ui-action-orders` | Empty-state heading | Cart is empty |
| `ui-state-error` · error | Validation, timeout, or service failure prevents confirmed submission | The order was not confirmed. Your information is preserved; retry uses the same checkout key. | `ui-action-retry-order`, `ui-action-orders` | Error summary linked to affected fields | Order was not submitted; review the error and retry |
| `ui-state-success` · success | The API returns the durable order ID | Order confirmed. The order ID and next fulfillment step are available. | `ui-action-orders` | Confirmation heading | Order confirmed |
| `ui-state-permission` · permission-denied | The session is missing, expired, or lacks the customer role | Sign in again to review this order. No order details are disclosed. | — | Permission heading | You are not authorized to review this order |
| `ui-state-offline` · offline | Connectivity is unavailable before confirmation | You appear to be offline. Your entered information remains local to this checkout session. | `ui-action-retry-order` | Offline status message | Offline; order has not been submitted |

#### Layout coverage

- `ui-compact`: 390×844; 4 regions placed.
- `ui-wide`: 1280×800; 4 regions placed.

## UI-to-system bindings

| Binding | Screen / region | Architecture target | Operation | Authorization | Loading | Error |
| --- | --- | --- | --- | --- | --- | --- |
| `ui-binding-submit-order` | `ui-screen-order-entry` / `ui-region-form` | `front-door` via `rel-web-frontdoor` | HTTPS/443 with OIDC access token and Idempotency-Key · Create order using the approved order API contract | Customer role and resource ownership validated at the API; the UI check is convenience, not the security boundary. | Disable repeat submit, preserve all data, expose busy state, and announce progress without animation. | Map typed errors to field summary or status panel; retain the same idempotency key for safe retry; never imply success without an order ID. |

## Accessibility contract

- **Target:** WCAG 2.2 Level AA
- **Keyboard:** All controls use native keyboard behavior; reading and focus order follows region order; no keyboard trap; retry and error-summary links are reachable.
- **Focus:** Set focus to the page heading on navigation, error summary on blocking validation, and confirmation heading after durable success; restore focus to the triggering action when a transient panel closes.
- **Screen Reader:** Use semantic landmarks/headings/forms, programmatic labels and errors, page titles, status announcements, and non-color state names; avoid duplicate live-region messages.
- **Contrast:** Semantic tokens must pass text and non-text contrast in default, hover, focus, disabled, error, and high-contrast states.
- **Zoom Reflow:** At 200% zoom and 320 CSS pixels, regions reflow to the compact layout without horizontal page scrolling or loss of content/actions.
- **Reduced Motion:** No animation or auto-advancing content is permitted; state changes are immediate, labeled, and announced when appropriate.

Verification:

- Automated axe-core checks in component and E2E CI
- Manual keyboard-only journey at compact and wide breakpoints
- Manual screen reader journey with NVDA and VoiceOver
- Contrast, high-contrast, 200% zoom, 320 CSS-pixel reflow, and text-spacing checks

## Implementation handoff

- **Front End:** Reuse the existing web application stack; for this standalone reference use React plus TypeScript as a proposed example, not a repository fact.
- **Design System Package:** Use the repository package when present; otherwise adopt Fluent UI React v9 behind product-owned wrapper components.
- **State Management:** Keep ephemeral form state local; represent server state with typed query keys and an explicit submission state machine.
- **Data Fetching:** Typed API client with OIDC token injection, correlation ID, bounded timeout, cancellation, and no automatic unsafe POST retry.
- **Validation:** Shared schema contract for client guidance plus authoritative server validation; map typed errors to fields and the error summary.
- **Testing:** Unit tests for state reducers and mapping, component tests for semantics/states, contract tests for API types, E2E success/error/offline/permission journeys, accessibility checks, and visual regression at both breakpoints.
- **Feature Flags:** Release behind an owned checkout-review flag with explicit default, audience, expiry, kill switch, and telemetry.
- **Observability:** Capture Web Vitals, route and submit latency, typed failure class, retry and abandonment counts, and correlation ID; redact order/customer content and tokens.
