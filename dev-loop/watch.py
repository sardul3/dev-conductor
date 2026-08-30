#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import config_dir


def watch_path(path: Path | None = None) -> Path:
    return path or (config_dir() / "watch.json")


def load_watch(path: Path | None = None) -> list[dict[str, Any]]:
    p = watch_path(path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        return [x for x in (data.get("prs") or []) if isinstance(x, dict)]
    return []


def save_watch(items: list[dict[str, Any]], path: Path | None = None) -> None:
    p = watch_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"prs": items}, indent=2) + "\n", encoding="utf-8")


def _same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return int(a.get("pr") or 0) == int(b.get("pr") or 0) and str(a.get("repo") or "") == str(b.get("repo") or "")


def add_watch(item: dict[str, Any], path: Path | None = None) -> list[dict[str, Any]]:
    items = load_watch(path)
    if any(_same(x, item) for x in items):
        return items
    items.append(item)
    save_watch(items, path)
    return items


def upsert_watch(item: dict[str, Any], path: Path | None = None) -> list[dict[str, Any]]:
    items = load_watch(path)
    out: list[dict[str, Any]] = []
    found = False
    for x in items:
        if _same(x, item):
            merged = dict(x)
            merged.update(item)
            out.append(merged)
            found = True
        else:
            out.append(x)
    if not found:
        out.append(item)
    save_watch(out, path)
    return out


def remove_watch(pr: int, repo: str, path: Path | None = None) -> list[dict[str, Any]]:
    items = [x for x in load_watch(path) if not (int(x.get("pr") or 0) == int(pr) and str(x.get("repo") or "") == repo)]
    save_watch(items, path)
    return items
