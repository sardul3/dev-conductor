#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import state_path


def load_state(path: Path | None = None) -> dict[str, Any]:
    p = path or state_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_state(data: dict[str, Any], path: Path | None = None) -> None:
    p = path or state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_state(path: Path | None = None, **kwargs: Any) -> dict[str, Any]:
    data = load_state(path)
    data.update(kwargs)
    save_state(data, path)
    return data
