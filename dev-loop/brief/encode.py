"""Token-cheap tables and scalars. Our name: brief (not AXI)."""
from __future__ import annotations

from typing import Any


def clip(text: Any, limit: int = 160, full: bool = False) -> str:
    s = "" if text is None else str(text)
    if full or limit <= 0 or len(s) <= limit:
        return s
    return f"{s[:limit]} (truncated, {len(s)} chars total — use --full)"


def cell(value: Any, *, limit: int = 160, full: bool = False) -> str:
    s = clip(value, limit=limit, full=full).replace("\n", " ").strip()
    if any(ch in s for ch in ",:\n") or s.startswith('"') or '"' in s:
        return '"' + s.replace('"', "'") + '"'
    return s


def encode_table(
    name: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    *,
    limit: int = 160,
    full: bool = False,
) -> list[str]:
    cols = [str(c) for c in columns[:4]]
    n = len(rows)
    lines = [f"{name}[{n}]{{{','.join(cols)}}}:" ]
    for row in rows:
        lines.append("  " + ",".join(cell(row.get(c, ""), limit=limit, full=full) for c in cols))
    return lines


def encode_meta(meta: dict[str, Any], *, limit: int = 160, full: bool = False) -> list[str]:
    lines: list[str] = []
    for key, val in meta.items():
        if val is None:
            continue
        if isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, (int, float)):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {clip(val, limit=limit, full=full)}")
    return lines
