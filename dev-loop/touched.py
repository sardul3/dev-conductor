#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except OSError:
        return ""
    return h.hexdigest()


def snapshot_tree(repo: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo).as_posix()
        if rel.startswith(".git/"):
            continue
        snap[rel] = _hash_file(p)
    return snap


def save_snapshot(path: Path, snap: dict[str, str]) -> None:
    path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_snapshot(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def changed_since(repo: Path, baseline: dict[str, str]) -> list[str]:
    now = snapshot_tree(repo)
    changed: list[str] = []
    for rel, digest in now.items():
        if baseline.get(rel) != digest:
            changed.append(rel)
    for rel in baseline:
        if rel not in now:
            changed.append(rel)
    return sorted(set(changed))
