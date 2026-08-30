# Dev-loop v1

Date: 2026-08-30
Status: implemented
Repo: `mac-ai-setup`

## Goal

Portable, token-cheap developer loop: Jira REST (not MCP) → repo memory → grill spec → isolated test-writer → TDD writer → verify → staff review → one conventional commit → `gh pr create`. Secrets stay in `~/.config/dev-conductor/secrets.env`. Live state stays in `~/.config/dev-conductor/dev-loop/` (not git).

## v1 path

1. **SessionStart** prints issue **keys only** when cwd is `~/dev` or a GitHub-remote git repo under `~/dev`. Skip: no git remote, remote is not GitHub, secrets missing (silent), extra denylist (empty by default). Cache ~10 minutes.
2. **`/dev-loop PROJ-123`** (`--repo` optional) runs the conductor. Target must be a GitHub-remote repo (or `--repo`).
3. Fetch issue JSON into `runs/PROJ-123/issue.json`.
4. **Repo memory**: SHA-256 of `HEAD` + tracked file contents. If unchanged, load `INDEX.md`. Else regenerate. No embeddings. Explore only when invalid/missing, then save. Public contracts = likely API files (controllers, OpenAPI, `*Client*`) capped.
5. **Spec**: launch Claude **without** skip marker so prompt-enrich grills. Skill `story-spec` writes `spec.md`. User approval writes `APPROVED`. Then conductor auto-runs the rest.
6. **Test-writer**: skip-marker work session. Spec + contracts only. PreToolUse denies Read/Grep/Glob of implementation paths while `state.stage == test-writer`. May patch tests only for compile/syntax/simple IO or spec contradiction.
7. **Writer**: existing `tdd` skill. Sees tests + spec + code.
8. **Verify** (local, not an LLM): infer Gradle/Maven/npm/go test+build. Optional `health` map in global yaml. Fail closed if no recipe. Cap 3 writer retries. No Snyk/Sonar/PIT.
9. **Review**: existing `code-reviewer` via `dev-loop-review`. Verdict file. excellent/good → ship. good-with-risks / needs_improvement / blocker → writer. Cap 3 then ship anyway with verdict in the PR. Does not re-run verify.
10. **Ship**: never commit to `main`/`master`. Always `git checkout -B feat/PROJ-123-slug` from the default branch. Snapshot working-tree hashes at branch time; stage only files whose hash changed. One conventional commit. `gh pr create` with Jira key in title, branch, body. Save `pr_number` in `state.json`. Dirty unrelated files stay unstaged.

## v2 (do not implement)

Poller (launchd + `gh`), auto-merge, stacked PRs, Jira transitions/deploy ticket, Snyk/Sonar/PIT (prefer 75% mutation, not 98%), screenshots, pr-comment-fixer, per-repo yaml.

## CLI

`python3 ~/.claude/hooks/dev-loop/cli.py` (after install) or `python3 dev-loop/cli.py` from this repo.

- `keys` — SessionStart
- `start KEY [--repo DIR]` — fetch, memory, spec launch
- `continue KEY` — after APPROVED: test-writer → writer → verify → review → ship
- `status` / `fetch` / `memory` / `verify` / `ship`

## Config

`~/.config/dev-conductor/dev-loop/config.yaml` copied from `dev-loop/config.yaml.example` if missing. One Jira `project`. `jql` is config. `health` and `verify` maps keyed by repo folder name.

## Install

`dev-loop/install.sh` (also from `bootstrap/install.sh`): copy Python to `~/.claude/hooks/dev-loop/`, copy command + skills, merge SessionStart + PreToolUse without wiping CCR env.

## Config

All knobs: `dev-loop/config.yaml.example`. Test profile (prod features off): `dev-loop/config.test.yaml`. Override path: `--config` or `DEVLOOP_CONFIG`. State dir: `DEVLOOP_HOME`.

## Plugin and Cursor

- Claude plugin: `plugins/dev-loop/` (skill copies for packaging; source of truth is `skills/`).
- Cursor: `cursor/dev-loop/` copies + rule. Do not change Claude-only files to make Cursor work.

## Eval

Fake Jira: `python3 dev-loop/fake_jira.py`. Five LAB stories in `dev-loop/testdata/jira/`. Lab app: `~/dev/devloop-lab` (allowlisted).
