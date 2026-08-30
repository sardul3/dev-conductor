#!/usr/bin/env python3
"""UserPromptSubmit: work-session brevity only. Skip grill. Back off on depth."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEPTH_REQUEST = re.compile(
    r"\b(thorough(ly)?|exhaustive(ly)?|comprehensive(ly)?|in\s+detail|detailed|"
    r"deep[\s-]?dive|step[\s-]by[\s-]step|full\s+(explanation|review|write[\s-]?up)|"
    r"walk\s+me\s+through|explain\s+(fully|everything)|tutorial|diagram)\b",
    re.IGNORECASE,
)

FULL = (
    "Work-session contract: lead with the change or command. No filler, no recap, "
    "no re-read loops. Search before whole-file reads. Trust a successful edit. "
    "Do not paste tool output back. Never skip a real test to save tokens."
)
SHORT = "Work session: no filler, no re-read loops. Depth request → write fully."
DEPTH = (
    "The user asked for depth. Drop terse output this turn. Still skip filler "
    "and do not restate the same point twice."
)


def decide(prompt: str, env: dict[str, str], turn: int) -> str | None:
    if env.get("PROMPT_ENRICH_WORK_SESSION") != "1":
        return None
    if env.get("TOKEN_EFFICIENCY_OFF") == "1" or env.get("PROMPT_ENRICH_DISABLE") == "1":
        return None
    if DEPTH_REQUEST.search(prompt or ""):
        return "depth"
    refresh = 10
    try:
        refresh = max(1, int(env.get("TOKEN_EFFICIENCY_REFRESH", "10")))
    except ValueError:
        refresh = 10
    if turn <= 1 or turn % refresh == 0:
        return "full"
    return "short"


def _text(kind: str) -> str:
    return {"full": FULL, "short": SHORT, "depth": DEPTH}.get(kind, SHORT)


def _state_path(session_id: str) -> Path:
    root = Path(os.environ.get("PROMPT_ENRICH_STATE_DIR") or Path.home() / ".claude" / "prompt-enrichment" / "state")
    return root / f"{session_id}.brevity.json"


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        session_id = str(payload.get("session_id") or "unknown")
        prompt = str(payload.get("user_prompt") or payload.get("user_input") or "")
        path = _state_path(session_id)
        turn = 1
        try:
            if path.is_file():
                turn = int(json.loads(path.read_text(encoding="utf-8")).get("turn") or 0) + 1
        except (OSError, json.JSONDecodeError, ValueError):
            turn = 1
        kind = decide(prompt, dict(os.environ), turn)
        if kind:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"turn": turn, "updated_at": datetime.now(timezone.utc).isoformat()}),
                    encoding="utf-8",
                )
            except OSError:
                pass
            print(
                json.dumps(
                    {
                        "continue": True,
                        "suppressOutput": True,
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": _text(kind),
                        },
                    }
                )
            )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
