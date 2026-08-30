#!/usr/bin/env python3
"""Apply durable agent-metadata updates from review feedback (verdict.metadata)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SECTION = "## Agent memory"
ALLOWED_TARGETS = frozenset({"agents", "rule", "context", "readme"})
DENIED_PATH_PARTS = (
    "secrets.env",
    "secrets.json",
    ".env",
    "credentials",
    "id_rsa",
    "id_ed25519",
    ".ssh/",
    "hooks/dev-loop",
)


class ApplyError(ValueError):
    """Unsafe or invalid memory update."""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _deny_path(rel: str) -> None:
    low = rel.replace("\\", "/").lower()
    for part in DENIED_PATH_PARTS:
        if part in low or low.endswith(part.rstrip("/")):
            raise ApplyError(f"refusing path that looks like secrets/hooks: {rel}")
    if low.startswith("/") or ".." in Path(rel).parts:
        raise ApplyError(f"refusing absolute or parent path: {rel}")


def _agents_file(repo: Path) -> Path:
    for name in ("AGENTS.md", "CLAUDE.md", "AGENT.md"):
        p = repo / name
        if p.is_file():
            return p
    return repo / "AGENTS.md"


def _ensure_bullet(body: str, text: str) -> tuple[str, bool]:
    bullet = f"- {text.strip()}"
    if _norm(text) in _norm(body):
        return body, False
    if SECTION not in body:
        body = body.rstrip() + f"\n\n{SECTION}\n\n{bullet}\n"
        return body, True
    # Append under existing section (before next ## or end)
    lines = body.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    inserted = False
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == SECTION:
            i += 1
            # keep blank / existing bullets until next heading
            while i < len(lines) and not lines[i].startswith("## "):
                out.append(lines[i])
                i += 1
            if out and not out[-1].endswith("\n"):
                out[-1] = out[-1] + "\n"
            out.append(bullet + "\n")
            inserted = True
            continue
        i += 1
    if not inserted:
        body = body.rstrip() + f"\n\n{SECTION}\n\n{bullet}\n"
        return body, True
    return "".join(out), True


def _write_rule(repo: Path, item: dict[str, Any]) -> dict[str, Any]:
    rel = str(item.get("path") or "").strip()
    if not rel:
        raise ApplyError("rule target requires path")
    _deny_path(rel)
    if bool(item.get("always_apply")):
        raise ApplyError("refusing always-on rules")
    globs = item.get("globs") or []
    if isinstance(globs, str):
        globs = [globs]
    if not isinstance(globs, list) or not globs:
        raise ApplyError("rule target requires globs")
    text = str(item.get("text") or "").strip()
    if not text:
        raise ApplyError("empty text")
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and _norm(text) in _norm(path.read_text(encoding="utf-8")):
        return {"target": "rule", "path": str(path), "status": "skipped"}
    glob_yaml = ", ".join(json.dumps(g) for g in globs)
    reason = str(item.get("reason") or "").strip()
    body = (
        "---\n"
        "description: Durable agent convention from review feedback\n"
        "alwaysApply: false\n"
        f"globs: [{glob_yaml}]\n"
        "---\n\n"
        f"{text}\n"
    )
    if reason:
        body += f"\n<!-- reason: {reason} -->\n"
    path.write_text(body, encoding="utf-8")
    return {"target": "rule", "path": str(path), "status": "applied"}


def apply_item(repo: Path, item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ApplyError("item must be an object")
    target = str(item.get("target") or "").strip().lower()
    if target not in ALLOWED_TARGETS:
        raise ApplyError(f"unknown target: {target or '(empty)'}")
    if item.get("durable") is False:
        raise ApplyError("refusing non-durable (one-off) item")
    text = str(item.get("text") or "").strip()
    if not text:
        raise ApplyError("empty text")
    if target == "rule":
        return _write_rule(repo, item)
    if target == "agents":
        path = _agents_file(repo)
        body = path.read_text(encoding="utf-8") if path.is_file() else "# Agent notes\n"
        new_body, changed = _ensure_bullet(body, text)
        if not changed:
            return {"target": "agents", "path": str(path), "status": "skipped"}
        path.write_text(new_body, encoding="utf-8")
        return {"target": "agents", "path": str(path), "status": "applied"}
    if target == "context":
        path = repo / str(item.get("path") or "CONTEXT.md")
        _deny_path(str(path.relative_to(repo)) if path.is_absolute() else str(item.get("path") or "CONTEXT.md"))
        rel = str(item.get("path") or "CONTEXT.md")
        path = repo / rel
        body = path.read_text(encoding="utf-8") if path.is_file() else "# Glossary\n"
        new_body, changed = _ensure_bullet(body, text)
        if not changed:
            return {"target": "context", "path": str(path), "status": "skipped"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_body, encoding="utf-8")
        return {"target": "context", "path": str(path), "status": "applied"}
    # readme
    path = repo / str(item.get("path") or "README.md")
    rel = str(item.get("path") or "README.md")
    _deny_path(rel)
    path = repo / rel
    body = path.read_text(encoding="utf-8") if path.is_file() else "# README\n"
    new_body, changed = _ensure_bullet(body, text)
    if not changed:
        return {"target": "readme", "path": str(path), "status": "skipped"}
    path.write_text(new_body, encoding="utf-8")
    return {"target": "readme", "path": str(path), "status": "applied"}


def apply_from_verdict(repo: Path, verdict: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(verdict, dict):
        return []
    items = verdict.get("metadata")
    if not isinstance(items, list) or not items:
        return []
    out: list[dict[str, Any]] = []
    for raw in items:
        try:
            out.append(apply_item(repo, raw if isinstance(raw, dict) else {}))
        except ApplyError as exc:
            out.append(
                {
                    "target": (raw or {}).get("target") if isinstance(raw, dict) else None,
                    "status": "rejected",
                    "error": str(exc),
                }
            )
    return out


def apply_verdict_file(repo: Path, verdict_path: Path) -> list[dict[str, Any]]:
    data = json.loads(verdict_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ApplyError("verdict.json must be an object")
    return apply_from_verdict(repo, data)
