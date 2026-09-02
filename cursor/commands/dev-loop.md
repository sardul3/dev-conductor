---
name: dev-loop
description: Run the Jira-to-PR conductor. Type /dev-loop KEY in Agent chat (optional --repo path).
---

Run the Jira → spec → tests → TDD → verify → review → PR conductor.

The rest of this message after `/dev-loop` is the Jira key and optional flags
(example: `/dev-loop LCN-2` or `/dev-loop LCN-2 --repo ~/dev/ai-trend-agent`).
If that text is empty, ask for the Jira key.

Prefer the `dev-loop` CLI (alias `dl`). Do not guess the repo.

If `--repo` is missing and cwd is not a git repo under `~/dev`, run `dev-loop repos`
and ask with a dropdown (plus “Create a new folder/repo”). Then:

```bash
dev-loop start KEY --repo PATH
```

Stay in this chat for `story-spec`. After the user approves the spec, write
`SPEC_APPROVED` then `dev-loop step KEY`. Each `step` is one stage. Test-writer
uses a new Agent. Do not use Jira or GitHub MCP.
