#!/usr/bin/env python3
"""Assemble the skip-marked prompt, runner script, and state for a clean Claude launch."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from route_model import Route, detect_backend, infer_profile, load_catalog, load_settings, resolve

SKIP_MARKER = "<!-- PROMPT_CONTRACT_V1 -->"
WORK_SESSION = """## Work session
Load `implement-terse`. No filler, no recap, no re-read loops.
Search before whole-file reads. Trust a successful edit. Do not paste tool output back.
Prefer `gh` over GitHub MCP. Jira/IdentityIQ MCP only if this repo `.mcp.json` enables them.
If I ask for depth, a tutorial, or a diagram, write fully.
"""
UNSET_CCR = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_BASE_URL",
    "CLAUDE_AGENT_API_BASE_URL",
    "CCR_CLAUDE_CODE_MODEL",
    "CODEXL_CLAUDE_CODE_MODEL",
)
SECTION = re.compile(r"(?im)^## ([^\n]+)\n(.*?)(?=^## |\Z)", re.S)
PROFILE_LINE = re.compile(r"(?im)^-\s*profile:\s*(\S+)")
OVERRIDE_LINE = re.compile(r"(?im)^-\s*override:\s*(\S+)")
MODEL_BLOCK = re.compile(r"(?im)^## Model\b.*?(?=^## |\Z)", re.S)


def _stamp(now_utc: str | None) -> str:
    if now_utc:
        return now_utc.replace(":", "-")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in SECTION.finditer(text):
        found[match.group(1).strip().lower()] = match.group(2).strip()
    return found


def ensure_skip_marker(text: str) -> str:
    body = text.strip() + "\n"
    if SKIP_MARKER in body:
        if not body.lstrip().startswith(SKIP_MARKER):
            body = re.sub(rf"\s*{re.escape(SKIP_MARKER)}\s*", "\n", body, count=1)
            return f"{SKIP_MARKER}\n{body.lstrip()}"
        return body if body.startswith(SKIP_MARKER) else f"{SKIP_MARKER}\n{body}"
    return f"{SKIP_MARKER}\n{body}"


def upsert_model_section(text: str, route: Route) -> str:
    block = (
        "## Model\n"
        f"- backend: {route.backend}\n"
        f"- profile: {route.profile}\n"
        f"- model: {route.primary}\n"
        f"- fallback: {route.fallback}\n"
        f"- why: {route.why}\n"
    )
    if MODEL_BLOCK.search(text):
        return MODEL_BLOCK.sub(block + "\n", text, count=1)
    return text.rstrip() + "\n\n" + block


def ensure_work_session_contract(text: str) -> str:
    if re.search(r"(?im)^## Work session\b", text):
        return text
    return text.rstrip() + "\n\n" + WORK_SESSION


def _write_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.update(payload)
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def _max_budget_usd(env: dict | None) -> str:
    raw = str((env or {}).get("DEVLOOP_MAX_BUDGET_USD") or "").strip()
    try:
        val = float(raw)
    except ValueError:
        return ""
    if val <= 0:
        return ""
    return f"{val:.4f}".rstrip("0").rstrip(".")


def _runner_script(cwd: str, prompt_file: Path, route: Route, env: dict | None = None) -> str:
    cd = shlex.quote(cwd)
    prompt = shlex.quote(str(prompt_file))
    primary = shlex.quote(route.primary)
    fallback = shlex.quote(route.fallback)
    budget = _max_budget_usd(env)
    budget_flag = f" --max-budget-usd {budget}" if budget else ""
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "export PROMPT_ENRICH_WORK_SESSION=1",
        f"cd {cd}",
    ]
    if route.backend == "anthropic":
        lines.append("unset " + " ".join(UNSET_CCR))
    lines.extend(
        [
            f"PROMPT_FILE={prompt}",
            'if ! command -v claude >/dev/null 2>&1; then',
            '  echo "claude not on PATH. Prompt saved at $PROMPT_FILE"',
            "  exit 1",
            "fi",
            f'exec claude --model {primary} --fallback-model {fallback}{budget_flag} "$(cat "$PROMPT_FILE")"',
            "",
        ]
    )
    return "\n".join(lines)


def prepare_launch(
    prompt_text: str,
    *,
    session_id: str,
    cwd: str,
    home: Path,
    project_dir: Path | None = None,
    backend: str | None = None,
    profile: str | None = None,
    override: str | None = None,
    env: dict[str, str] | None = None,
    catalog_path: Path | None = None,
    now_utc: str | None = None,
) -> dict:
    env = env if env is not None else dict(os.environ)
    catalog = load_catalog(catalog_path)
    settings = {}
    settings_path = Path(home) / ".claude" / "settings.json"
    if settings_path.is_file():
        settings = load_settings(settings_path)
    chosen_backend = backend or detect_backend(env, settings)
    sections = _sections(prompt_text)
    chosen_profile = profile or (PROFILE_LINE.search(prompt_text).group(1) if PROFILE_LINE.search(prompt_text) else None)
    if not chosen_profile:
        chosen_profile = infer_profile(
            sections.get("goal", ""),
            sections.get("context", ""),
            sections.get("output format", sections.get("format", "")),
        )
    chosen_override = override or env.get("PROMPT_ENRICH_MODEL_OVERRIDE") or (
        OVERRIDE_LINE.search(prompt_text).group(1) if OVERRIDE_LINE.search(prompt_text) else None
    )
    route = resolve(chosen_profile, chosen_backend, chosen_override, catalog=catalog)
    stamped = _stamp(now_utc)
    runs = Path(home) / ".claude" / "prompt-enrichment" / "runs" / session_id
    runs.mkdir(parents=True, exist_ok=True)
    prompt_file = runs / f"enriched-{stamped}.md"
    state_path = Path(home) / ".claude" / "prompt-enrichment" / "state" / f"{session_id}.json"
    _write_state(
        state_path,
        {
            "phase": "launching",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "cwd": cwd,
            "backend": route.backend,
            "model_profile": route.profile,
            "model_id": route.primary,
            "fallback_id": route.fallback,
        },
    )
    body = ensure_work_session_contract(upsert_model_section(ensure_skip_marker(prompt_text), route))
    prompt_file.write_text(body, encoding="utf-8")
    copied = None
    dest_root = Path(project_dir) if project_dir else Path(cwd)
    try:
        prompts_dir = dest_root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        copied = prompts_dir / prompt_file.name
        copied.write_text(body, encoding="utf-8")
    except OSError:
        copied = None
    runner_file = runs / "launch.sh"
    runner_file.write_text(_runner_script(cwd, prompt_file, route, env), encoding="utf-8")
    runner_file.chmod(0o755)
    _write_state(
        state_path,
        {
            "phase": "handed_off",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "backend": route.backend,
            "model_profile": route.profile,
            "model_id": route.primary,
            "fallback_id": route.fallback,
            "prompt_file": str(prompt_file),
        },
    )
    return {
        "backend": route.backend,
        "profile": route.profile,
        "primary": route.primary,
        "fallback": route.fallback,
        "why": route.why,
        "prompt_file": str(prompt_file),
        "runner_file": str(runner_file),
        "project_copy": str(copied) if copied else None,
        "state_file": str(state_path),
    }


def open_new_terminal(runner: str) -> bool:
    """Open iTerm2 if installed, else Terminal.app. Returns False if AppleScript fails."""
    cmd = f"bash {shlex.quote(runner)}"
    quoted = json.dumps(cmd)
    if Path("/Applications/iTerm.app").exists():
        script = (
            "tell application \"iTerm\"\n"
            "  activate\n"
            "  create window with default profile\n"
            "  tell current session of current window\n"
            f"    write text {quoted}\n"
            "  end tell\n"
            "end tell"
        )
    else:
        script = (
            "tell application \"Terminal\"\n"
            "  activate\n"
            f"  do script {quoted}\n"
            "end tell"
        )
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        return result.returncode == 0
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a clean Claude Code launch")
    parser.add_argument("--file", dest="prompt_file", default="")
    parser.add_argument("--session", default=os.environ.get("CLAUDE_SESSION_ID") or "manual")
    parser.add_argument("--cwd", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--backend", default="")
    parser.add_argument("--profile", default="")
    parser.add_argument("--override", default="")
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR") or "")
    args = parser.parse_args()
    if args.prompt_file:
        text = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        text = __import__("sys").stdin.read()
    if not text.strip():
        raise SystemExit("no prompt text")
    result = prepare_launch(
        text,
        session_id=args.session,
        cwd=args.cwd,
        home=Path(args.home),
        project_dir=Path(args.project_dir) if args.project_dir else Path(args.cwd),
        backend=args.backend or None,
        profile=args.profile or None,
        override=args.override or None,
        env=dict(os.environ),
    )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
