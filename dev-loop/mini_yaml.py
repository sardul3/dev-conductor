#!/usr/bin/env python3
"""Tiny YAML subset: mappings, lists, scalars, comments. No tags/anchors."""

from __future__ import annotations

from typing import Any


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s in {"", "~", "null", "Null", "NULL"}:
        return None
    if s in {"true", "True", "TRUE"}:
        return True
    if s in {"false", "False", "FALSE"}:
        return False
    if (s.startswith("'") and s.endswith("'") and len(s) >= 2) or (
        s.startswith('"') and s.endswith('"') and len(s) >= 2
    ):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in inner.split(",") if p.strip()]
    if s.startswith("{") and s.endswith("}"):
        return {}
    try:
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    except ValueError:
        pass
    return s


def loads(text: str) -> Any:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if "#" in raw:
            in_sq = in_dq = False
            cut = len(raw)
            for i, ch in enumerate(raw):
                if ch == "'" and not in_dq:
                    in_sq = not in_sq
                elif ch == '"' and not in_sq:
                    in_dq = not in_dq
                elif ch == "#" and not in_sq and not in_dq:
                    cut = i
                    break
            raw = raw[:cut]
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    if not lines:
        return {}

    def parse_block(idx: int, indent: int) -> tuple[Any, int]:
        if idx >= len(lines):
            return {}, idx
        _, content = lines[idx]
        if content.startswith("- "):
            items: list[Any] = []
            while idx < len(lines) and lines[idx][0] == indent and lines[idx][1].startswith("- "):
                item_raw = lines[idx][1][2:].strip()
                idx += 1
                if item_raw and ":" in item_raw and not item_raw.startswith("{"):
                    key, _, rest = item_raw.partition(":")
                    node: dict[str, Any] = {key.strip(): _parse_scalar(rest) if rest.strip() else None}
                    if idx < len(lines) and lines[idx][0] > indent:
                        nested, idx = parse_block(idx, lines[idx][0])
                        if rest.strip() in {"", None} or node[key.strip()] is None:
                            node[key.strip()] = nested
                        elif isinstance(nested, dict):
                            node.update(nested)
                    items.append(node)
                else:
                    items.append(_parse_scalar(item_raw))
            return items, idx

        mapping: dict[str, Any] = {}
        while idx < len(lines) and lines[idx][0] == indent:
            key, _, rest = lines[idx][1].partition(":")
            key = key.strip()
            rest = rest.strip()
            idx += 1
            if rest:
                mapping[key] = _parse_scalar(rest)
            elif idx < len(lines) and lines[idx][0] > indent:
                mapping[key], idx = parse_block(idx, lines[idx][0])
            else:
                mapping[key] = {}
        return mapping, idx

    value, _ = parse_block(0, lines[0][0])
    return value
