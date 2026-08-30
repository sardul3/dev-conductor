#!/usr/bin/env python3
"""PreToolUse: block plan-mode and implementation while interviewing or after handoff."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLAN_TOOLS = {"EnterPlanMode", "enter_plan_mode", "SwitchMode", "switch_mode"}
EXPLORE_TOOLS = {"Agent", "Task", "Glob", "Grep", "WebFetch", "WebSearch", "Explore", "Write", "Edit", "NotebookEdit"}
HANDED_OFF_EXTRA = {"Bash", "BashTool"}
GRILL_PHASES = {"enriching", "grilling"}
HANDED_OFF_PHASES = {"handed_off", "launching"}

GRILL_REASON = (
    "Enrichment session: interview first. Do not explore the repo or enter plan mode. "
    "Ask numbered grill questions. Read only the listed SKILL.md files."
)
HANDOFF_REASON = (
    "Handoff already opened a work session in a new tab. Do not implement here — "
    "two sessions on OpenRouter will 429. Tell the user work continues in the new terminal and stop. "
    "To implement in this tab instead: /skip-enrich"
)


def should_block(payload: dict, phase: str | None) -> bool:
    name = str(payload.get("tool_name") or payload.get("toolName") or "")
    if phase in HANDED_OFF_PHASES:
        return name in EXPLORE_TOOLS or name in HANDED_OFF_EXTRA or name in PLAN_TOOLS
    if phase not in GRILL_PHASES:
        return False
    if name in EXPLORE_TOOLS:
        return True
    if name not in PLAN_TOOLS:
        return False
    if name.lower() in {"switchmode", "switch_mode"}:
        inp = payload.get("tool_input") or payload.get("toolInput") or {}
        mode = str(inp.get("mode") or inp.get("target") or "").lower()
        return mode in {"plan", "planning"} or not mode
    return True


def deny_reason(phase: str | None) -> str:
    if phase in HANDED_OFF_PHASES:
        return HANDOFF_REASON
    return GRILL_REASON


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        session_id = str(payload.get("session_id") or "unknown")
        state_dir = Path(
            os.environ.get("PROMPT_ENRICH_STATE_DIR")
            or Path.home() / ".claude" / "prompt-enrichment" / "state"
        )
        phase = None
        path = state_dir / f"{session_id}.json"
        if path.is_file():
            try:
                phase = json.loads(path.read_text(encoding="utf-8")).get("phase")
            except (OSError, json.JSONDecodeError):
                phase = None
        phase_s = str(phase) if phase else None
        if should_block(payload, phase_s):
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": deny_reason(phase_s),
                        }
                    }
                )
            )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
