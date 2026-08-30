#!/usr/bin/env python3
"""File-backed Jira Cloud REST subset for eval (no network to Atlassian)."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent / "testdata" / "jira"

# In-memory overlay so POST transitions/comments work without rewriting fixtures.
STORE: dict[str, dict] = {"comments": {}, "status": {}}

TRANSITIONS = {
    "transitions": [
        {"id": "11", "name": "In Progress"},
        {"id": "21", "name": "In Review"},
        {"id": "31", "name": "Done"},
        {"id": "41", "name": "Blocked"},
        {"id": "51", "name": "Waiting"},
    ]
}
ID_TO_NAME = {t["id"]: t["name"] for t in TRANSITIONS["transitions"]}


def _issue_parts(path: str) -> tuple[str, list[str]]:
    rest = path.split("/rest/api/3/issue/", 1)[-1] if "/rest/api/3/issue/" in path else ""
    bits = [b for b in rest.split("/") if b]
    key = bits[0] if bits else ""
    return key, bits[1:]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send(self, code: int, payload: dict | None) -> None:
        raw = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.endswith("/rest/api/3/search/jql") or path.endswith("/rest/api/3/search"):
            self._send(200, json.loads((ROOT / "search.json").read_text(encoding="utf-8")))
            return
        if "/rest/api/3/issue/" in path:
            key, rest = _issue_parts(path)
            if rest == ["transitions"]:
                self._send(200, TRANSITIONS)
                return
            f = ROOT / f"{key}.json"
            if not f.is_file():
                self._send(404, {"errorMessages": [f"{key} not found"]})
                return
            data = json.loads(f.read_text(encoding="utf-8"))
            fields = data.setdefault("fields", {})
            if STORE["status"].get(key):
                fields.setdefault("status", {})["name"] = STORE["status"][key]
            extra = STORE["comments"].get(key) or []
            if extra:
                block = fields.setdefault("comment", {"comments": []})
                block.setdefault("comments", []).extend(extra)
            self._send(200, data)
            return
        self._send(404, {"errorMessages": ["not found"]})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        payload = self._read_json()
        if "/rest/api/3/issue/" not in path:
            self._send(404, {"errorMessages": ["not found"]})
            return
        key, rest = _issue_parts(path)
        if rest == ["transitions"]:
            tid = str(((payload.get("transition") or {}).get("id")) or "")
            if tid in ID_TO_NAME:
                STORE["status"][key] = ID_TO_NAME[tid]
            self._send(204, None)
            return
        if rest == ["comment"]:
            comments = STORE["comments"].setdefault(key, [])
            comments.append(
                {
                    "author": {"displayName": "dev-loop"},
                    "body": payload.get("body") or payload,
                }
            )
            self._send(201, {"id": str(len(comments))})
            return
        self._send(404, {"errorMessages": ["not found"]})


def serve(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    httpd = serve(args.host, args.port)
    print(f"fake-jira http://{args.host}:{args.port}  (ctrl-c to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
