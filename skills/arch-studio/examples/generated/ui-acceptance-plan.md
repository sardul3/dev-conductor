# UI acceptance plan: Retail order integration

> Execute these scenarios against the implemented UI at every supported breakpoint. A generated plan is not test evidence.

## Goal-level journeys

### `ui-flow-submit-order` · Review and submit an order

**Given** Customer has an authenticated session; Cart has at least one available item; A stable checkout idempotency key exists

**When** on `ui-screen-order-entry` the user reviews items, quantities, totals, and delivery information
**Then** The complete order summary and editable fields are available in logical reading order
**And when the exception occurs:** Unavailable items are identified inline and submission remains disabled until resolved.

**And** on `ui-screen-order-entry` the user activates Submit order once
**Then** The action is disabled, the same idempotency key is sent, progress is announced, and duplicate activation is prevented
**And when the exception occurs:** A network or service error preserves entered data and offers a retry with the same key.

**And** on `ui-screen-order-entry` the user reviews the confirmed order ID
**Then** A durable confirmation, next step, and navigation to orders are available and announced

Expected goal outcomes:

- Exactly one order is created
- The customer receives an order ID
- Submission status is understandable without motion or color alone

Exception coverage:

- Validation error
- Permission or session failure
- Offline or timeout
- Backend rejection with retry-safe correlation ID

## Screen-state contract tests

### `ui-screen-order-entry` · Review and submit order

- [ ] `default` / `ui-state-default`: when Order data and authorization are available, show “Review order details and submit when the summary is correct.”; expose only ui-action-submit-order, ui-action-orders; move focus to Page heading on initial navigation; preserve current focus after inline edits; announce “Order review loaded”.
- [ ] `loading` / `ui-state-loading`: when Order query is pending with no usable cached result, show “Loading the order summary; controls are not exposed until labels and values are available.”; expose only no actions; move focus to Keep focus on the initiating navigation target; announce “Loading order review”.
- [ ] `empty` / `ui-state-empty`: when The order contains no purchasable items, show “Your cart is empty. Add an item before checkout.”; expose only ui-action-orders; move focus to Empty-state heading; announce “Cart is empty”.
- [ ] `error` / `ui-state-error`: when Validation, timeout, or service failure prevents confirmed submission, show “The order was not confirmed. Your information is preserved; retry uses the same checkout key.”; expose only ui-action-retry-order, ui-action-orders; move focus to Error summary linked to affected fields; announce “Order was not submitted; review the error and retry”.
- [ ] `success` / `ui-state-success`: when The API returns the durable order ID, show “Order confirmed. The order ID and next fulfillment step are available.”; expose only ui-action-orders; move focus to Confirmation heading; announce “Order confirmed”.
- [ ] `permission-denied` / `ui-state-permission`: when The session is missing, expired, or lacks the customer role, show “Sign in again to review this order. No order details are disclosed.”; expose only no actions; move focus to Permission heading; announce “You are not authorized to review this order”.
- [ ] `offline` / `ui-state-offline`: when Connectivity is unavailable before confirmation, show “You appear to be offline. Your entered information remains local to this checkout session.”; expose only ui-action-retry-order; move focus to Offline status message; announce “Offline; order has not been submitted”.
- [ ] `ui-compact`: all 4 regions render without overlap, clipping, horizontal page scroll, or lost action access.
- [ ] `ui-wide`: all 4 regions render without overlap, clipping, horizontal page scroll, or lost action access.

## UI-to-system contract tests

### `ui-binding-submit-order` · Create order using the approved order API contract

- [ ] Request contract: Validated order draft, delivery selection, terms acknowledgement, correlation ID, and stable idempotency key; no secrets or analytics payload.
- [ ] Response contract: Confirmed order ID and status, or a typed validation/auth/transient/permanent error with safe customer message and correlation ID.
- [ ] Authorization: Customer role and resource ownership validated at the API; the UI check is convenience, not the security boundary.
- [ ] Loading behavior: Disable repeat submit, preserve all data, expose busy state, and announce progress without animation.
- [ ] Error behavior: Map typed errors to field summary or status panel; retain the same idempotency key for safe retry; never imply success without an order ID.
- [ ] Architecture trace: `front-door` / `rel-web-frontdoor`

## Accessibility and quality gates

Target: **WCAG 2.2 Level AA**

- [ ] Automated axe-core checks in component and E2E CI
- [ ] Manual keyboard-only journey at compact and wide breakpoints
- [ ] Manual screen reader journey with NVDA and VoiceOver
- [ ] Contrast, high-contrast, 200% zoom, 320 CSS-pixel reflow, and text-spacing checks
- [ ] Keyboard order and visible focus match the documented landmarks, actions, dialogs, and recovery path.
- [ ] Screen-reader names, roles, values, instructions, errors, live announcements, and page titles match the state contract.
- [ ] Text and non-text contrast, target size, zoom/reflow, orientation, and text spacing pass at supported breakpoints.
- [ ] Authentication does not depend on a cognitive-function test; repeated data entry and accessible authentication requirements are verified.
- [ ] Automated accessibility, component, integration, end-to-end, and visual-regression suites run in CI with owned failure thresholds.
- [ ] No animation is introduced; state changes remain understandable without motion.
