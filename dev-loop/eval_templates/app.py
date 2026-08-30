from __future__ import annotations

import json
from typing import Any

_TASKS: dict[int, dict[str, Any]] = {}
_NEXT = 1


def reset() -> None:
    global _NEXT
    _TASKS.clear()
    _NEXT = 1


def handle(method: str, path: str, body: bytes = b"") -> tuple[int, Any]:
    global _NEXT
    method = method.upper()
    path = path.rstrip("/") or "/"
    if method == "GET" and path == "/health":
        return 200, {"status": "ok"}
    if method == "POST" and path == "/tasks":
        try:
            data = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            return 400, {"error": "invalid json"}
        title = (data.get("title") or "").strip()
        if not title:
            return 400, {"error": "title required"}
        tid = _NEXT
        _NEXT += 1
        item = {"id": tid, "title": title, "status": "todo"}
        _TASKS[tid] = item
        return 201, item
    if method == "GET" and path == "/tasks":
        return 200, list(_TASKS.values())
    if method == "GET" and path.startswith("/tasks/"):
        rest = path[len("/tasks/"):]
        try:
            tid = int(rest)
        except ValueError:
            return 404, {"error": "not found"}
        item = _TASKS.get(tid)
        if not item:
            return 404, {"error": "not found"}
        return 200, item
    if method == "POST" and "/complete" in path:
        mid = path[len("/tasks/"):].replace("/complete", "").strip("/")
        try:
            tid = int(mid)
        except ValueError:
            return 404, {"error": "not found"}
        item = _TASKS.get(tid)
        if not item:
            return 404, {"error": "not found"}
        item["status"] = "done"
        return 200, item
    return 404, {"error": "not found"}
