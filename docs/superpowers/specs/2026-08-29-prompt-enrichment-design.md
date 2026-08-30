# Prompt enrichment pipeline (hook + skills + clean Claude session)

Date: 2026-08-29  
Status: implemented (unit tests + install; Claude Code round-trip still needed)  
Repo: `dev-conductor`  
Approved in chat: thin classifier hook; **own** design-tree interview + handoff skills (not the mattpocock plugin); dual CCR/Anthropic model routing; layered CLAUDE.md; Auto-run on new tasks only.

## 1. Goal

When a user submits a *new* substantial task to Claude Code, fill a prompt-engineering contract, interview until the deep ask is clear, **pick a model profile** (Claude has no native Auto mode), then run the real work in a **new Claude Code process** with a clean context window and `claude --model …`.

## 2. Non-goals

- Do not rewrite or interview **every** message (follow-ups, “yes”, slash commands, grill answers).
- Do not implement the user’s task in the enrichment session.
- Do not open a Cursor Agent tab (not a hook API). Handoff is Claude CLI in a new terminal only.
- Do not put API keys, SSH private keys, or CCR tokens in prompts or state files.
- Do not use Claude Code’s `type: prompt` UserPromptSubmit hook as the classifier (that reuses the session model and tool schema). A **tiny side-call** (Y/N, no tools) after deterministic skips is allowed.
- Do not pick a model in the submit hook. Model routing happens **after** the contract is complete, using the gathered context.
- Do not pretend this is vendor Auto mode. It is our router at launch time.
- Do not assume CCR. The same install must work on stock Claude Code (Anthropic aliases) and on CCR/OpenRouter. Pick the catalog at launch from the live environment, not from this Mac’s current settings baked into skills.

## 3. Components

| Unit | What it does | How you use it | Depends on |
| ---- | ------------- | -------------- | ---------- |
| `prompt-enrich` hook | Classifies skip vs new-task; injects skill instructions | Installed in `~/.claude/settings.json` | State dir, skip marker |
| `design-tree-interview` | Own grilling primitive (frontier rounds, recommend answers, subagent for facts) | Auto when grilling | This repo `skills/` |
| `grill-plan` / `grill-plan-docs` | User invoke; docs variant also runs `domain-glossary` | `/grill-plan` | Same |
| `session-handoff` | Compact to temp/runs file with skip marker | After frontier empty | Same |
| `restate-plain` | Re-pitch last turn in simple English | User lost | Same |
| `implement-terse` | Caveman-like output in the **work** session only | Handoff suggests it | Same |
| `route-model` | Detects CCR vs stock Claude Code; maps profile → model id | After `phase=ready` | `model-router.yaml` |
| `launch-clean-claude.sh` | Writes the structured prompt and opens `claude --model` in a new terminal | Called only when the contract is complete | `claude` on PATH, Terminal or iTerm |

## 4. Data flow

```text
UserPromptSubmit
  → hook reads stdin JSON (session_id, user_prompt, cwd)
  → if SKIP: exit 0, no extra context
  → if NEW TASK: write state phase=enriching; stdout additionalContext
       "Read ~/.claude/skills/prompt-contract/SKILL.md then
        ~/.claude/skills/grill-deep-ask/SKILL.md.
        Do not implement. Do not launch yet."
  → this session: fill contract → grill → choose model_profile → assemble prompt
  → route-model.py detects backend (ccr | anthropic), then profile → ids
  → launch-clean-claude.sh writes prompts/enriched-<ts>.md
       first line: <!-- PROMPT_CONTRACT_V1 -->
  → new terminal: cd <cwd> && [env policy] claude --model "$PRIMARY" --fallback-model "$FALLBACK" "$(cat prompt-file)"
  → new session hook sees skip marker → no second enrich
```

## 5. Prompt contract (9 required constructs)

Multiselect allowed for role, audience, and length/tone. Infer when obvious; only ask for missing *high-impact* slots.

| # | Slot | Examples | Required |
| - | ---- | -------- | -------- |
| 1 | Role | senior backend engineer, staff SRE, staff iOS, tech lead, security reviewer | yes |
| 2 | Audience | the implementing agent, a PR reviewer, a beginner, future-me | yes |
| 3 | Goal | the deep ask in one sentence plus the actual deliverable | yes |
| 4 | Context | repo, stack, files, constraints already known | yes (may be “none / infer from repo”) |
| 5 | Constraints / non-goals | must / must not | yes |
| 6 | Output format | code+tests, plan only, diff, ADR, commands | yes |
| 7 | Length / tone | short, informal, rigorous, production-ready | yes |
| 8 | Success criteria | observable done-when | yes |
| 9 | Model profile | `fast` `code` `reason` `heavy` `vision` (auto; user may override) | yes |

Optional (ask only if they change the work): examples, tools/sources, reasoning style (plan-then-code vs jump-to-code). Do not ask the user to name a raw model id unless they volunteer an override.

Assembled prompt shape:

```markdown
<!-- PROMPT_CONTRACT_V1 -->
# Task
...
## Role
...
## Audience
...
## Goal
...
## Context
...
## Constraints
...
## Output format
...
## Length and tone
...
## Success criteria
...
## Model
- backend: ccr | anthropic
- profile: code
- model: <id for that backend>
- fallback: <id>
- why: implementation + tests; coding specialist
## Original user request
...
```

## 5.1 Auto model routing (CCR and stock Claude Code)

Claude Code has no Auto mode. Once the contract is filled, the session chooses a **profile** (`fast` `code` `reason` `heavy` `vision`). `route-model.py` (1) detects **backend**, (2) maps profile → ids from YAML. Launch uses `claude --model` / `--fallback-model`.

Profiles are backend-agnostic. Only the YAML ids change.

### Backend detection (first match wins)

1. `PROMPT_ENRICH_BACKEND=ccr` or `=anthropic` (explicit override).
2. **ccr** if any of these is set in the process or in `~/.claude/settings.json` `env`:
   - `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_BASE_URL` / `CLAUDE_AGENT_API_BASE_URL` pointing at localhost/127.0.0.1 (typical `:3456`)
   - `apiKeyHelper` path containing `claude-code-router`
   - `CCR_CLAUDE_CODE_MODEL` or `CODEXL_CLAUDE_CODE_MODEL`
3. Else **anthropic** (stock Claude Code: Anthropic API, aliases like `sonnet` / `opus` / `haiku` / `fable`).

Do not hardcode OpenRouter ids in skills. Skills only emit a profile (and optional override string).

### Catalog A — `ccr` (OpenRouter via Claude Code Router)

| Profile | When | Primary | Fallback |
| ------- | ---- | ------- | -------- |
| `fast` | short/informal, lookup, tiny edit, plan-only | `OpenRouter/inclusionai/ling-3.0-flash:free` | `OpenRouter/nvidia/nemotron-3-nano-30b-a3b:free` |
| `code` | implement, refactor, tests, patches | `OpenRouter/cohere/north-mini-code:free` | `OpenRouter/poolside/laguna-s-2.1:free` |
| `reason` | debug, design, investigate, architecture | `OpenRouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | `OpenRouter/nvidia/nemotron-3-super-120b-a12b:free` |
| `heavy` | large multi-file, production, security | `OpenRouter/nvidia/nemotron-3-ultra-550b-a55b:free` | `OpenRouter/nvidia/nemotron-3-super-120b-a12b:free` |
| `vision` | screenshots, UI, diagrams, VL | `OpenRouter/nvidia/nemotron-nano-12b-v2-vl:free` | `OpenRouter/openrouter/free` |

Launch **inherits** the current Claude env (CCR gateway stays).

### Catalog B — `anthropic` (plain Claude Code, no CCR)

Use CLI aliases so we do not pin dated snapshots (`claude --help`: `sonnet`, `opus`, `fable`; `haiku` if the CLI accepts it).

| Profile | When | Primary | Fallback |
| ------- | ---- | ------- | -------- |
| `fast` | short/informal, lookup, tiny edit, plan-only | `haiku` (if rejected by CLI, `fable`) | `sonnet` |
| `code` | implement, refactor, tests, patches | `sonnet` | `opus` |
| `reason` | debug, design, investigate, architecture | `opus` | `sonnet` |
| `heavy` | large multi-file, production, security | `opus` | `sonnet` |
| `vision` | screenshots, UI, diagrams | `sonnet` | `opus` |

Launch **must not** send stock Claude Code through a leftover CCR proxy. For `anthropic` backend, the new terminal command unsets `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_BASE_URL`, `CLAUDE_AGENT_API_BASE_URL`, `CCR_CLAUDE_CODE_MODEL`, `CODEXL_CLAUDE_CODE_MODEL` in that process only. `install.sh` does not delete those keys from `settings.json` on a CCR machine.

`route-model.py` validates `haiku`: if the environment documents it as unavailable, YAML `fast.primary_alt: fable` is used.

### Shared rules

- Tie-break (same on both backends): `vision` if images/UI screenshots; else `heavy` if many files / production / security; else `reason` if debug/design/investigate; else `code` if output is code/tests; else `fast`.
- User override wins: “use opus”, “use ultra”, “use sonnet”, or a profile name. Override is resolved **in the active catalog** (e.g. “opus” on CCR is ignored unless YAML defines an alias; prefer profile names for portability). Optional YAML `aliases:` map `opus` → anthropic `opus` and ccr `OpenRouter/nvidia/nemotron-3-ultra-550b-a55b:free` if we want friendly names on both.
- Unknown profile → `code`. Unknown override id → log and use profile mapping.
- Config: `claude/prompt-enrich/model-router.yaml` with top-level keys `ccr:` and `anthropic:`. Installed to `~/.claude/prompt-enrichment/model-router.yaml`.
- Enrichment session stays on whatever model that session already uses. Only the **work** session is routed.
- Routing is once per new session. Wrong pick → re-launch, not mid-chat swap.
- CCR rate limits / Anthropic usage limits: try fallback; if `claude` fails to start, keep the prompt file and print the command.

**Who decides:** grilling session picks profile + why; `route-model.py` maps ids; user override wins.

## 6. Classifier

Evaluate in order. First match wins. **Do not grow a verb list.**

**Skip (no LLM)** if any of:

1. `user_prompt` contains `<!-- PROMPT_CONTRACT_V1 -->`
2. Trimmed prompt starts with `/skip-enrich`
3. Trimmed prompt starts with `/` **and** is not `/deep-ask`
4. State `phase` in `{enriching, grilling, launching}`
5. Follow-up regex (yes/ok/do it/…) under 80 characters
6. Env `PROMPT_ENRICH_DISABLE=1`

**Force inject** if trimmed prompt starts with `/deep-ask`.

**Otherwise:** one cheap Anthropic-format `messages` call (no tools, thinking disabled, `max_tokens=8`) to CCR. Default `OpenRouter/poolside/laguna-s-2.1:free`. Reply `Y` or `N`. Timeout ~2.5s, parse error, 429, or CCR down → **skip** (fail open). Do not use Claude Code’s `type: prompt` hook (session model + tool schema).

Env: `PROMPT_ENRICH_CLASSIFIER_MODEL`, `PROMPT_ENRICH_CLASSIFIER_URL`, `PROMPT_ENRICH_CLASSIFIER_TIMEOUT`.

Hook must fail **open** (exit 0, no inject) on parse errors so Claude stays usable.

## 7. Grill protocol (`design-tree-interview`)

Own recreation of upstream grilling **behavior** (not a copy of the plugin). Wrapper: `grill-plan`. Docs variant: `grill-plan-docs` + `domain-glossary`.

- Work a **design tree** in **rounds**. Each round asks the full **frontier** (every question whose prerequisites are settled). Number them. Always give a recommended answer. Wait.
- Facts: look up (subagent if large). Decisions: ask the user.
- Max **8 rounds** (not 8 questions). Then proceed with listed assumptions.
- Fill contract slots from the tree; infer; do not spend a round on model id unless they override.
- Then `session-handoff` → `launch-clean-claude.sh`. Handoff file is the new-session payload (not a giant 12-section dump of files that already exist).
- Escape: “just go”, “skip grill”, `/skip-enrich`.
- `restate-plain` if they are lost mid-grill.
- Work session loads `implement-terse`; grill session must not.

## 8. Launch

Script: `~/.claude/hooks/prompt-enrich/launch-clean-claude.sh` (copy in repo under `claude/prompt-enrich/`).

1. Require `claude` on PATH.
2. Run `route-model.py` on the assembled contract; record primary, fallback, and why in the prompt’s Model section and in state (`model_id`, `fallback_id`, `model_profile`).
3. Write the assembled markdown to  
   `$HOME/.claude/prompt-enrichment/runs/<session_id>/enriched-<utc>.md`  
   and copy to `$CLAUDE_PROJECT_DIR/prompts/enriched-<utc>.md` if that dir is writable (`prompts/` gitignored in this repo).
4. Set state `phase=launching`.
5. Open a new terminal in `cwd`:
   - Build argv: `claude --model "$PRIMARY" --fallback-model "$FALLBACK"` plus the prompt file contents as the initial user message.
   - If backend is `anthropic`: prefix the command so CCR proxy env vars are unset for that process only.
   - If backend is `ccr`: inherit env.
   - iTerm2 if present, else Terminal.app.
6. Set state `phase=done` with `backend`, `model_profile`, `model_id`, `fallback_id`.

The enrichment session must **not** start implementing after launch. It should print the file path and “work continues in the new terminal”.

If `claude` is missing: write the file anyway, print the path, do not fail the whole session.

## 9. State

Path: `$HOME/.claude/prompt-enrichment/state/<session_id>.json`

```json
{
  "phase": "idle|enriching|grilling|ready|launching|done",
  "updated_at": "ISO-8601",
  "cwd": "/path",
  "backend": "ccr|anthropic",
  "model_profile": "code",
  "model_id": "sonnet",
  "fallback_id": "opus"
}
```

No prompt text stored if it might contain secrets; store phase only. Assembled prompts live in `runs/` and should still be treated as possibly sensitive (local only, gitignore).

## 10. File layout (this repo)

```text
claude/prompt-enrich/
  hooks.json                 # snippet to merge into ~/.claude/settings.json
  classify.py                # UserPromptSubmit classifier
  prompt_log.py              # summarize / redact Messages bodies
  prompt_log_proxy.py        # :3457 log + forward to CCR
  ensure_prompt_log_proxy.sh # SessionStart: start proxy, rewrite session BASE_URL
  model-router.yaml          # ccr: and anthropic: profile → model ids
  route-model.py             # detect backend, resolve profile + overrides
  launch-clean-claude.sh
  install.sh                 # copy skills + hook, merge settings
skills/prompt-contract/SKILL.md
skills/prompt-contract/reference.md
skills/design-tree-interview/SKILL.md
skills/grill-plan/SKILL.md
skills/grill-plan-docs/SKILL.md
skills/domain-glossary/SKILL.md
skills/session-handoff/SKILL.md
skills/restate-plain/SKILL.md
skills/implement-terse/SKILL.md
claude/memory/README.md
claude/memory/user.CLAUDE.md
claude/memory/project.CLAUDE.md
claude/memory/rules/java-spring-temporal.md
docs/superpowers/specs/2026-08-29-prompt-enrichment-design.md
```

Install targets: `~/.claude/hooks/prompt-enrich/`, `~/.claude/skills/prompt-contract/`, `~/.claude/skills/grill-deep-ask/`. Merge `hooks.UserPromptSubmit` without wiping existing `settings.json` keys (CCR env, permissions).

## 11. Error handling

| Failure | Behavior |
| ------- | -------- |
| Hook JSON parse fail | fail open |
| State dir unwritable | fail open |
| Grill exceeds 8 questions | launch with assumptions |
| `claude` missing | save file, tell user to paste |
| New terminal AppleScript fail | save file, print command to run by hand |
| Nested enrich in new session | skip marker prevents it |
| Unknown backend / mixed env | Prefer explicit `PROMPT_ENRICH_BACKEND`; else detection rules |
| Anthropic launch on a CCR laptop | Unset proxy env in the child only; do not rewrite `settings.json` |

## 12. Testing

- Unit tests for `classify.py`: skip marker, `/skip-enrich`, `/deep-ask`, short “yes”, long “implement auth”, slash `/compact`.
- Unit tests for `route-model.py`:
  - `PROMPT_ENRICH_BACKEND=ccr` → OpenRouter ids; `=anthropic` → aliases
  - detect ccr from `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`
  - detect anthropic when those env vars are absent
  - each profile on both catalogs; vision beats code; unknown profile → `code`; override wins
- Manual on a CCR machine and, if available, on stock Claude Code: launch shows the right `--model` and anthropic launches do not keep `ANTHROPIC_BASE_URL`.
- Manual: submit a new-task prompt in Claude Code, confirm inject; reply “yes”, confirm no inject; complete grill; confirm new terminal uses `--model` for the chosen profile and skip marker on the launched prompt.
- Do not claim the hook works until those classifier tests pass and one manual Claude Code round-trip is observed.

## 13. Open choices (locked)

- Trigger: new-task auto, not every prompt.
- Handoff: new `claude` CLI terminal, not Cursor tabs, not same-session implement.
- Classifier: deterministic hard skips, then a tiny Y/N side-call (fail open). Not Claude Code `type: prompt`.
- Interview: current session, then clean session for the work.
- Auto model: after context, profile → id at launch. Two catalogs (`ccr` OpenRouter ids, `anthropic` CLI aliases). Backend auto-detected; `PROMPT_ENRICH_BACKEND` overrides. Stock launches unset CCR proxy env.
- Skills: own recreations (`design-tree-interview`, `grill-plan`, `session-handoff`, …), not `claude plugins install mattpocock-skills`.
- Memory: layered CLAUDE.md + path-scoped rules; Caveman/`implement-terse` only on work sessions.

## 14. Layered CLAUDE.md

See `claude/memory/README.md`. Root project CLAUDE.md stays lean and is the only layer guaranteed after `/compact`. Nested CLAUDE.md is lazy. Java/Temporal goes in path-scoped rules. User file is preferences only.
