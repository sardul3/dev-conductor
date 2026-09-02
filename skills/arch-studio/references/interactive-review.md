# Interactive specification review

`review.html` is a static, self-contained review workspace. It has no animation and requires no server for ordinary review.

## Review objects

Reviewers can set `pending`, `accepted`, `rejected`, or `modify` and attach a comment to every architecture view, component, connection, decision, risk, open question, governance/Kubernetes/UI finding, UI screen, region, action, state, user-flow step, UI component, and the overall design.

The browser stores draft decisions locally for the current project and version. Use **Export review JSON** for the authoritative handoff. The export includes project ID and version, model digest, timestamp, reviewer name if supplied, decisions, and an overall disposition. If the digest does not match the current model, treat the review as stale.

**Copy Claude prompt** creates a bounded instruction containing only rejected or modify decisions and their comments, plus the project, version, and digest. Claude must inspect the current canonical model, apply the smallest coherent change, preserve architecture and UI stable IDs, update affected ADRs, risks, screen states, bindings, acceptance coverage, and traceability, and rerun strict build.

An acceptance is not permission to deploy. It approves only the reviewed visual specification at the recorded digest.

## Local server

Use `serve` when decisions should be persisted to disk or when the chat panel should connect to Claude Code. The server binds only to `127.0.0.1`, uses a per-run anti-CSRF token and same-origin checks, caps request sizes, serializes bridge requests, writes atomically, retains a model backup, and never uses a shell or permission-bypass mode.

The bridge is off by default. `--claude-bridge` enables a constrained, headless Claude Code call. If `--claude-session <id-or-name>` is supplied, the call resumes that conversation; otherwise the first message creates a dedicated review session and later messages resume it.

Claude has no tools and must return structured JSON containing a reviewer-facing reply and a complete candidate model. The server independently validates the candidate and regenerates only after structural validation. Strict gate failures remain visible and are never relabeled as a pass.

Pause another terminal that is actively using the same Claude session. The review server serializes its own requests but cannot coordinate a separately running client.

## Review closure

Close review only when the model digest matches, every rejected or modify item is resolved or explicitly deferred, strict build passes or eligible blockers have current waivers, decisions and risks are current, and all artifacts were regenerated together.
