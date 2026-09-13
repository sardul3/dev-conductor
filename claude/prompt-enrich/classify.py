#!/usr/bin/env python3
"""UserPromptSubmit classifier: hard skips, then a 1-token LLM. Fail open."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

SKIP_MARKER = "<!-- PROMPT_CONTRACT_V1 -->"
FOLLOW_UP = re.compile(
    r"^(y|yes|yep|yeah|no|nope|ok|okay|k|sure|thanks|thx|continue|resume|"
    r"retry|proceed|next|go|go ahead|keep going|pick up|"
    r"do it|do that|lgtm|please|wait|nvm|nevermind|fix that|try again|"
    r"same|more|less)\.?$",
    re.IGNORECASE,
)
MID_PHASES = {"enriching", "grilling", "launching"}
DEFAULT_CLASSIFIER_MODEL = "haiku"
CLASSIFIER_PROMPT = (
    "Classify the user message for Claude Code. Reply with one character only.\n"
    "Y = new substantial task that should be interviewed before coding "
    "(feature, hardening, architecture, non-trivial bug).\n"
    "N = follow-up, glance at a log/paste, chit-chat, or tiny question.\n"
    "Message:\n<<<\n{msg}\n>>>"
)

INJECT_CONTEXT = """SYSTEM: New substantial task. This is the ENRICHMENT session, not the work session.

You MUST NOT: implement, enter plan mode, spawn Explore/Task/Agent, Glob, Grep, or use the Write tool.
You MUST: ask numbered design-tree interview questions with a recommended answer each. Wait for the user.
Allowed tools: Read, Skill, AskUserQuestion, Bash (save_handoff.py + launch-clean-claude.sh only).
AskUserQuestion: at most 4 options per question.

Facts: Read only cwd README.md, package.json, pyproject.toml, go.mod, Cargo.toml, composer.json if present. Do not ask the user the stack if those files already say.

1. Read ~/.claude/skills/prompt-contract/SKILL.md
2. Follow ~/.claude/skills/design-tree-interview/SKILL.md
3. When the frontier is empty, pipe the contract to:
   python3 ~/.claude/hooks/prompt-enrich/save_handoff.py
   then run ~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <printed-path>
   Never Write to /tmp.

Work continues in a new `claude` terminal. This session only interviews and hands off. After launch, stop. Do not implement in this tab.
"""


def extract_prompt(payload: dict) -> str:
    for key in ("user_prompt", "prompt", "text", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def log_decision(path: Path, record: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return


def parse_yn(text: str) -> str | None:
    blob = (text or "").strip().upper()
    if not blob:
        return None
    if blob[:1] in {"Y", "N"}:
        return blob[:1]
    if re.search(r"\bY\b", blob) and not re.search(r"\bN\b", blob):
        return "Y"
    if re.search(r"\bN\b", blob) and not re.search(r"\bY\b", blob):
        return "N"
    return None


def _assistant_text(payload: dict) -> str:
    bits: list[str] = []
    for block in payload.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            bits.append(str(block["text"]))
    return "".join(bits)


def _api_key(env: dict[str, str]) -> str:
    key = (env.get("ANTHROPIC_API_KEY") or "").strip()
    if key:
        return key
    helper = (env.get("CLAUDE_CODE_API_KEY_HELPER") or "").strip()
    if not helper:
        settings_path = Path.home() / ".claude" / "settings.json"
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            helper = str(settings.get("apiKeyHelper") or "")
        except (OSError, json.JSONDecodeError):
            helper = ""
    if not helper:
        return ""
    try:
        return subprocess.check_output(
            helper,
            shell=False,
            timeout=2,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def llm_classify(prompt: str, env: dict[str, str] | None = None) -> str:
    env = env if env is not None else dict(os.environ)
    base = (
        env.get("PROMPT_ENRICH_CLASSIFIER_URL")
        or env.get("ANTHROPIC_BASE_URL")
        or env.get("ANTHROPIC_API_BASE_URL")
        or "https://api.anthropic.com"
    ).rstrip("/")
    model = env.get("PROMPT_ENRICH_CLASSIFIER_MODEL") or DEFAULT_CLASSIFIER_MODEL
    key = _api_key(env)
    if not key:
        raise RuntimeError("no classifier key")
    timeout = 2.5
    try:
        timeout = float(env.get("PROMPT_ENRICH_CLASSIFIER_TIMEOUT") or "2.5")
    except ValueError:
        timeout = 2.5
    body = {
        "model": model,
        "max_tokens": 8,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": CLASSIFIER_PROMPT.format(msg=prompt[:800])}],
    }
    encoded = json.dumps(body).encode("utf-8")
    last_error: Exception | None = None
    payload: dict = {}
    for attempt in range(2):
        req = urllib.request.Request(
            f"{base}/v1/messages",
            data=encoded,
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt == 0:
                time.sleep(0.6)
                continue
            raise
    else:
        raise last_error or RuntimeError("classifier failed")
    yn = parse_yn(_assistant_text(payload))
    if yn is None:
        yn = parse_yn(json.dumps(payload))
    if yn is None:
        raise RuntimeError("unparseable classifier reply")
    return yn


def _state_path(state_dir: Path, session_id: str) -> Path:
    return state_dir / f"{session_id}.json"


def _read_phase(state_dir: Path, session_id: str) -> str | None:
    path = _state_path(state_dir, session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        phase = data.get("phase")
        return str(phase) if phase else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_phase(state_dir: Path, session_id: str, phase: str, cwd: str | None) -> bool:
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        path = _state_path(state_dir, session_id)
        payload = {
            "phase": phase,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "cwd": cwd or "",
        }
        existing = {}
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        existing.update(payload)
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def classify(
    user_prompt: str,
    session_id: str,
    state_dir: Path,
    env: dict[str, str],
    llm: Callable[[str], str] | None = None,
) -> str:
    if str(env.get("PROMPT_ENRICH_DISABLE", os.environ.get("PROMPT_ENRICH_DISABLE", ""))) == "1":
        return "skip"
    text = user_prompt or ""
    trimmed = text.strip()
    if not trimmed:
        return "skip"
    if SKIP_MARKER in text:
        return "skip"
    if trimmed.startswith("/skip-enrich"):
        _write_phase(state_dir, session_id, "done", None)
        return "skip"
    if trimmed.startswith("/deep-ask"):
        return "inject"
    if trimmed.startswith("/"):
        return "skip"
    phase = _read_phase(state_dir, session_id)
    if phase in MID_PHASES:
        return "skip"
    if len(trimmed) < 80 and FOLLOW_UP.match(trimmed):
        return "skip"
    decide = llm if llm is not None else (lambda msg: llm_classify(msg, env))
    try:
        verdict = decide(trimmed)
    except Exception:
        return "skip"
    return "inject" if str(verdict).strip().upper().startswith("Y") else "skip"


def hook_response(decision: str) -> dict:
    if decision != "inject":
        return {"continue": True, "suppressOutput": True}
    return {
        "continue": True,
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": INJECT_CONTEXT,
        },
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    prompt = extract_prompt(payload)
    session_id = str(payload.get("session_id") or "unknown")
    cwd = str(payload.get("cwd") or "")
    state_dir = Path(
        os.environ.get("PROMPT_ENRICH_STATE_DIR") or Path.home() / ".claude" / "prompt-enrichment" / "state"
    )
    log_path = Path(
        os.environ.get("PROMPT_ENRICH_HOOK_LOG")
        or Path.home() / ".claude" / "prompt-enrichment" / "hook-log.jsonl"
    )
    try:
        decision = classify(prompt, session_id, state_dir, dict(os.environ))
        if decision == "inject" and not _write_phase(state_dir, session_id, "enriching", cwd):
            decision = "skip"
        log_decision(
            log_path,
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "decision": decision,
                "session_id": session_id,
                "cwd": cwd,
                "prompt_chars": len(prompt),
                "preview": prompt[:160],
            },
        )
        print(json.dumps(hook_response(decision)))
    except Exception as exc:
        log_decision(
            log_path,
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "decision": "error",
                "session_id": session_id,
                "error": str(exc)[:240],
            },
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
