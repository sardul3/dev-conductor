---
name: test-writer
description: Write failing tests from spec.md and public contracts only, with no production code and no Read of implementation trees. Use in the /dev-loop test-writer stage, when the conductor wrote prompt-test-writer.md, or when the user says write the failing tests for this ticket. Parent chat must Task a new Agent for this work.
---

# Test-writer

These tests are the **contract** the writer must turn green. If you Read `src/main` (or equivalent) you will accidentally test internals, and refactors will break the suite for the wrong reason.

## Who runs this

**Parent** (`/dev-loop` chat): do not Grep/Read implementation. Task a **new Agent** whose prompt is `prompt-test-writer.md` from the run dir (or this skill + `spec.md` + `contracts.md` only). After the child writes `STAGE_DONE`:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py step KEY
```

**Child:** follow the rest of this skill. Write tests, then `STAGE_DONE` and `SESSION_DONE` in the run dir from the prompt.

## Inputs

- `spec.md` seams and Given/When/Then (source of truth)
- `contracts.md` / OpenAPI / proto if present
- Stack manifests only, to find the test runner: `package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`, `go.mod` — not implementation sources

Run dir: `~/.config/dev-conductor/dev-loop/runs/KEY/`.

## What to test

**Public seams** are observable product behavior: HTTP routes, exported functions, the **app** CLI (`python -m pkg`), events. Scaffolding / greenfield tickets: test the **app stub** (importable package, greeting on stdout), not the toolchain.

**Forbidden as test subjects** (README + conductor `cli.py verify`, not pytest):

- package-manager sync (`uv sync`, `npm install`)
- nested test runners (`uv run pytest`, `pytest`, `npm test`, `go test ./...`) — deadlock
- linters / typecheckers (`ruff`, `pyright`, `eslint`)
- lockfile existence, `requires-python`, “does pytest/ruff exit 0”
- toolchain install
- README command lists

Never spawn `uv run pytest` or `pytest` from a test. Never `git add` `__pycache__` or `.venv`. New Python repo: add a standard `.gitignore`.

## Procedure

1. Read spec seams. Skip verify/README gates (uv/ruff/pyright/pytest-exits-0). Each remaining **product** case becomes one (or one parameterized) test whose name reads like the spec.
2. Infer the test command from manifests so you can **run the suite once**. Do not assert that command from inside a test.
3. Write tests that call **only product seams**. Prefer one vertical slice (the story’s primary behavior). Extra cases only if the spec names product behavior.
4. Cover named error/edge paths as behavioral tests, not line-coverage theatre.
5. Run the test command once. Confirm failures are assertion/behavior failures (red for the right reason), not missing imports you can fix in the test file.
6. Do not implement production code. Do not mock the unit under test into emptiness (a fake that always returns `"ok"` is not a test).
7. Do not git commit. Write `STAGE_DONE` and `SESSION_DONE`.

Do not later “fix” tests to match buggy code except compile/syntax/simple IO or a spec contradiction.

## Example shape (pytest-style; copy the shape)

```python
def test_given_app_running_when_get_health_then_200_status_ok(client):
    # Given the app is running (client fixture)
    # When GET /health with no auth
    response = client.get("/health")
    # Then
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

Forbidden: `from app.internal.health import _check` or reading `src/main` to see how it is implemented.
