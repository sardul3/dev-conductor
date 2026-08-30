from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from brief.encode import clip, encode_meta, encode_table


@dataclass
class Document:
    bin: str
    description: str
    meta: dict[str, Any] = field(default_factory=dict)
    # name -> (columns, rows)
    tables: dict[str, tuple[list[str], list[dict[str, Any]]]] = field(default_factory=dict)
    help: list[str] = field(default_factory=list)
    empty_hint: str = "0 results"

    def add_table(self, name: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
        self.tables[name] = (list(columns)[:4], list(rows))


def _row_count(doc: Document) -> int:
    return sum(len(rows) for _, rows in doc.tables.values())


def emit(doc: Document, *, fmt: str = "brief", full: bool = False, clip_at: int = 160) -> str:
    fmt = (fmt or "brief").strip().lower()
    if fmt == "json":
        return _json(doc, full=full, clip_at=clip_at)
    return _brief(doc, full=full, clip_at=clip_at)


def _brief(doc: Document, *, full: bool, clip_at: int) -> str:
    lines = [
        f"bin: {doc.bin}",
        f"description: {clip(doc.description, limit=clip_at, full=full)}",
    ]
    lines.extend(encode_meta(doc.meta, limit=clip_at, full=full))
    count = _row_count(doc)
    lines.append(f"count: {count}")
    if count == 0 and doc.tables:
        lines.append(f"empty: {doc.empty_hint}")
    for name, (cols, rows) in doc.tables.items():
        lines.extend(encode_table(name, cols, rows, limit=clip_at, full=full))
    helps = [h for h in doc.help if h]
    if helps:
        lines.append(f"help[{len(helps)}]:")
        for h in helps:
            lines.append(f"  {h}")
    return "\n".join(lines) + "\n"


def _clip_obj(val: Any, *, full: bool, clip_at: int) -> Any:
    if isinstance(val, str):
        return clip(val, limit=clip_at, full=full)
    if isinstance(val, dict):
        return {k: _clip_obj(v, full=full, clip_at=clip_at) for k, v in val.items()}
    if isinstance(val, list):
        return [_clip_obj(v, full=full, clip_at=clip_at) for v in val]
    return val


def _json(doc: Document, *, full: bool, clip_at: int) -> str:
    tables = {}
    for name, (cols, rows) in doc.tables.items():
        slim = [{c: row.get(c) for c in cols} for row in rows]
        tables[name] = _clip_obj(slim, full=full, clip_at=clip_at)
    payload = {
        "bin": doc.bin,
        "description": doc.description,
        "meta": _clip_obj(doc.meta, full=full, clip_at=clip_at),
        "count": _row_count(doc),
        "tables": tables,
        "help": list(doc.help),
    }
    if payload["count"] == 0 and doc.tables:
        payload["empty"] = doc.empty_hint
    return json.dumps(payload, ensure_ascii=False) + "\n"


def fail(message: str, *, code: int = 1) -> int:
    print(emit(Document(bin="dev-loop", description="error", meta={"error": message})))
    return code


def note(message: str) -> None:
    print(f"dev-loop: {message}")
