---
name: dev-loop
description: Run the Jira-to-PR conductor. Type /dev-loop KEY in Agent chat (optional --repo path).
---

Run the Jira → spec → tests → TDD → verify → review → PR conductor.

The rest of this message after `/dev-loop` is the Jira key and optional flags
(example: `/dev-loop LCN-2` or `/dev-loop LCN-2 --repo ~/dev/ai-trend-agent`).
If that text is empty, do not guess. Fetch keys + repos as JSON and pick both
with **AskQuestion** (never paste CLI `--help` into chat).

Prefer the `dev-loop` CLI (alias `dl`). Do not guess the repo.

If the key or `--repo` is missing and cwd is not a **git** repo under `~/dev`:

```bash
dev-loop keys --format json
# if count is 0:
dev-loop keys --recent --format json
dev-loop repos --format json
```

One AskQuestion: ticket (`tickets[].key`) and repo (`candidates[].label` plus
create). Prefer `kind: git`. Empty/`folder` cwd is not a repo — `init-repo`
first. Then:

```bash
dev-loop start KEY --repo PATH
```

After `start` and each `step`, if stdout or `dev-loop progress KEY` shows
`workspace` / `dev-loop: workspace PATH`, immediately call Cursor
`cursor-app-control` `move_agent_to_root` with `rootPath` = that path.
Inspect the schema via GetDynamicTools first. Mandatory in Cursor — do not
grill or write in the clone. Isolation worktrees are `{repo}-worktrees/{KEY}`
next to the clone (no leading dot).

Stay in this chat for `story-spec`. Grill with AskQuestion (recommended option
first). After the user approves the spec, run `dev-loop approve KEY` (one
command: record approval + next stage). Do not write handshake files by hand.
Each later `step` is one stage. Test-writer uses a new Agent.
Do not use Jira or GitHub MCP.

Ship writes the GitHub PR: Jira browse link, concrete verify commands, visual
evidence (png/video in `runs/KEY/evidence/` for every ticket; backend: terminal
snapshots of tests/run/curl; verify.log is not enough). No spec excerpt.
Never bare `Jira: KEY`.
