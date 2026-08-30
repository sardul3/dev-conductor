"""Subclass Connector; view() applies brief rules. Implement fetch() only."""
from __future__ import annotations

from typing import Any, ClassVar

from brief.document import Document, emit

REGISTRY: dict[str, type["Connector"]] = {}
CLI_BIN = "python3 ~/.claude/hooks/dev-loop/cli.py"


def register(cls: type["Connector"]) -> type["Connector"]:
    if cls.name:
        REGISTRY[cls.name] = cls
    return cls


class Connector:
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    table_name: ClassVar[str] = "items"
    columns: ClassVar[tuple[str, ...]] = ()
    help: ClassVar[tuple[str, ...]] = ()
    clip_at: ClassVar[int] = 160
    bin: ClassVar[str] = CLI_BIN

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls is not Connector and getattr(cls, "name", ""):
            register(cls)

    def fetch(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def document(self, data: dict[str, Any], **kwargs: Any) -> Document:
        rows = data.get(self.table_name)
        if not isinstance(rows, list):
            rows = data.get("items") if isinstance(data.get("items"), list) else []
        cols = list(self.columns) or _infer_columns(rows)
        meta = {k: v for k, v in data.items() if k not in {self.table_name, "items"} and not isinstance(v, list)}
        doc = Document(bin=self.bin, description=self.description, meta=meta, help=list(self.help))
        if self.columns or rows or self.table_name:
            doc.add_table(self.table_name, cols, list(rows) if isinstance(rows, list) else [])
        return doc

    def view(self, *, fmt: str = "brief", full: bool = False, **kwargs: Any) -> str:
        data = self.fetch(**kwargs)
        return emit(self.document(data, **kwargs), fmt=fmt, full=full, clip_at=self.clip_at)


def _infer_columns(rows: list[Any]) -> list[str]:
    if not rows or not isinstance(rows[0], dict):
        return ["value"]
    return [str(k) for k in list(rows[0].keys())[:4]]
