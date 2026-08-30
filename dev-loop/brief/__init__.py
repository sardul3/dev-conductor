"""Brief: agent I/O kit for dev-conductor.

New connector tomorrow: subclass `Connector`, set name / columns / help, implement fetch().
`view()` applies clip, 3–4 columns, count, empty, help[]. Disk files stay JSON.
"""
from brief.connector import CLI_BIN, REGISTRY, Connector, register
from brief.document import Document, emit, fail, note
from brief.encode import clip, encode_table

__all__ = [
    "CLI_BIN",
    "REGISTRY",
    "Connector",
    "Document",
    "clip",
    "emit",
    "encode_table",
    "fail",
    "note",
    "register",
]

from brief import ports as _ports  # noqa: F401  — register built-ins
