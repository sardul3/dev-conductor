---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.css"
  - "**/*.scss"
  - "**/package.json"
  - "**/pnpm-lock.yaml"
  - "**/yarn.lock"
  - "**/package-lock.json"
  - "**/next.config.*"
  - "**/vite.config.*"
  - "**/tsconfig.json"
---

# TypeScript / web product

Loads when TS/JS, CSS, or Node package files are in play.

## Language and structure

- Strict TypeScript. No `any` on new code; `unknown` + narrowing at boundaries. Prefer the repo’s existing framework (Next, Vite, etc.) over introducing a second one.
- Server vs client: secrets, privileged fetches, and provider keys stay on the server. Do not put API keys in `NEXT_PUBLIC_*` or Vite `import.meta.env` unless they are meant to be public.
- Shared types for API contracts. Do not drift UI types from OpenAPI / server DTOs without updating both.

## UI

- New or restyled surfaces: spawn `design-lead` / follow `frontend-design`. Refuse generic AI palettes, Inter/Roboto defaults, purple-on-white gradients, and interchangeable card grids.
- Accessibility is part of done: keyboard path, labels, contrast, focus. Do not ship icon-only controls without an accessible name.
- Loading, empty, and error states are real UI, not an afterthought. Optimistic updates must reconcile with server truth.

## Data and state

- Single source of truth for server state (the repo’s query library or equivalent). Do not duplicate the same resource in ad-hoc `useEffect` fetches across pages.
- Forms: schema validation on the client for UX and again on the server. Never trust the client for authz or prices.
- Pagination and filters belong in the URL when they are shareable.

## Testing and quality

- Component tests for user-visible behavior; Playwright/Cypress for critical flows when the repo has them. Do not snapshot-only as the only coverage.
- Bundle: no accidental Node modules in the client graph. Fail CI on secret-scanning and high-severity npm audits when those gates exist.

## LLM in the browser

- Model calls from the client only through your backend. Stream with backpressure. Cap tokens. Do not persist chat logs with PII in `localStorage` unless that is an explicit product decision with a retention policy.
