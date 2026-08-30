#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_status(run: Path) -> dict[str, Any]:
    p = run / "status.json"
    if not p.is_file():
        return {"ticket": run.name, "current": None, "history": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ticket": run.name, "current": None, "history": []}
    if not isinstance(data, dict):
        return {"ticket": run.name, "current": None, "history": []}
    data.setdefault("ticket", run.name)
    data.setdefault("history", [])
    return data


def current(run: Path) -> dict[str, Any] | None:
    cur = load_status(run).get("current")
    return cur if isinstance(cur, dict) else None


def render_progress(ticket: str, cur: dict[str, Any] | None, history: list[dict[str, Any]]) -> str:
    stage = (cur or {}).get("stage") or "unknown"
    status = (cur or {}).get("status") or "unknown"
    lines = [
        f"# {ticket}",
        "",
        f"**Now:** {stage} / {status}",
        "",
        "Handshake files: SPEC_APPROVED (spec accepted), SESSION_DONE (this agent session finished).",
        "",
        "| time (UTC) | stage | status | note |",
        "|---|---|---|---|",
    ]
    for ev in history:
        lines.append(
            "| {at} | {stage} | {status} | {note} |".format(
                at=ev.get("at") or "",
                stage=ev.get("stage") or "",
                status=ev.get("status") or "",
                note=(ev.get("note") or ev.get("artifact") or "").replace("|", "/"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def record(run: Path, stage: str, status: str, **extra: Any) -> dict[str, Any]:
    run.mkdir(parents=True, exist_ok=True)
    data = load_status(run)
    event = {"at": _now(), "stage": stage, "status": status}
    for k, v in extra.items():
        if v is not None:
            event[k] = v
    hist = list(data.get("history") or [])
    hist.append(event)
    data["history"] = hist
    data["current"] = {"stage": stage, "status": status}
    if extra.get("ticket"):
        data["ticket"] = extra["ticket"]
    (run / "status.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (run / "progress.md").write_text(
        render_progress(str(data.get("ticket") or run.name), data["current"], hist),
        encoding="utf-8",
    )
    return data


def backfill(run: Path) -> dict[str, Any]:
    """If status.json is missing, infer a timeline from handshake files."""
    data = load_status(run)
    if data.get("history"):
        return data
    key = run.name
    if (run / "issue.json").is_file() or (run / "issue.md").is_file():
        record(run, "fetch", "ok", ticket=key, note="backfill")
    if (run / "spec.md").is_file():
        approved = (run / "APPROVED").is_file() or (run / "SPEC_APPROVED").is_file()
        if approved:
            if not (run / "SPEC_APPROVED").is_file():
                (run / "SPEC_APPROVED").write_text("spec approved\n", encoding="utf-8")
            record(run, "spec", "approved", ticket=key, note="backfill from APPROVED (spec only)")
        else:
            record(run, "spec", "waiting_approval", ticket=key, artifact="spec.md", note="backfill")
    elif (run / "STAGE_DONE").is_file() or (run / "SESSION_DONE").is_file():
        record(run, "session", "done", ticket=key, note="backfill STAGE_DONE — which stage is unknown")
    return load_status(run)
