#!/usr/bin/env python3
"""PostToolUse: after launch-clean-claude.sh, tell this tab to stop implementing."""

from __future__ import annotations

import json
import sys

STOP = (
    "SYSTEM: Handoff launched a new Claude tab. This enrichment session is closed for implementation. "
    "Do not Write, Edit, or run further Bash. Reply in one sentence that work continues in the new terminal, then stop. "
    "Implementing here as well doubles OpenRouter load and causes 429s."
)


def is_launch(payload: dict) -> bool:
    name = str(payload.get("tool_name") or payload.get("toolName") or "")
    if name not in {"Bash", "BashTool"}:
        return False
    inp = payload.get("tool_input") or payload.get("toolInput") or {}
    cmd = ""
    if isinstance(inp, dict):
        cmd = str(inp.get("command") or "")
    elif isinstance(inp, str):
        cmd = inp
    return "launch-clean-claude.sh" in cmd


def hook_response() -> dict:
    return {
        "continue": True,
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": STOP,
        },
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        if is_launch(payload):
            print(json.dumps(hook_response()))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
