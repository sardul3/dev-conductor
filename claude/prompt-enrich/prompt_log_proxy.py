#!/usr/bin/env python3
"""Local reverse proxy: log Claude Code Messages requests, then forward to CCR.

Claude Code hooks never receive system + tools. This process sits on
ANTHROPIC_BASE_URL (default :3457) and forwards to CCR (:3456).
Does not thin payloads yet — log only, fail open.
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from prompt_log import write_capture

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade", "host"}


def _split_upstream(spec: str) -> tuple[str, int]:
    raw = spec.strip()
    if "://" in raw:
        parts = urlsplit(raw)
        host = parts.hostname or "127.0.0.1"
        port = parts.port or 80
        return host, port
    if ":" in raw:
        host, _, port_s = raw.rpartition(":")
        return host or "127.0.0.1", int(port_s)
    return raw, 80


class PromptLogHandler(BaseHTTPRequestHandler):
    server: "PromptLogServer"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle()

    def do_OPTIONS(self) -> None:
        self._handle()

    def _handle(self) -> None:
        if self.path in {"/health", "/__prompt_log/health"}:
            payload = b'{"ok":true,"service":"prompt-log-proxy"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.command == "POST" and self.path.split("?", 1)[0] in {
            "/v1/messages",
            "/v1/messages/count_tokens",
        }:
            self._log_body(raw)
        self._forward(raw)

    def _log_body(self, raw: bytes) -> None:
        try:
            body = json.loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                return
            write_capture(self.server.log_dir, body, req_path=self.path.split("?", 1)[0])
        except Exception as exc:
            sys.stderr.write(f"prompt-log capture skipped: {exc}\n")

    def _forward(self, raw: bytes) -> None:
        headers = {}
        for key, val in self.headers.items():
            if key.lower() in HOP:
                continue
            headers[key] = val
        if raw:
            headers["Content-Length"] = str(len(raw))
        host, port = self.server.upstream
        conn = http.client.HTTPConnection(host, port, timeout=self.server.timeout)
        try:
            conn.request(self.command, self.path, body=raw or None, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                if key.lower() in HOP:
                    continue
                self.send_header(key, val)
            self.end_headers()
            if self.command == "HEAD":
                return
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (OSError, http.client.HTTPException) as exc:
            msg = json.dumps({"error": {"type": "proxy_error", "message": str(exc)}}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(msg)
        finally:
            conn.close()


class PromptLogServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, listen: tuple[str, int], upstream: tuple[str, int], log_dir: Path, timeout: float = 600.0):
        super().__init__(listen, PromptLogHandler)
        self.upstream = upstream
        self.log_dir = log_dir
        self.timeout = timeout


def main() -> int:
    parser = argparse.ArgumentParser(description="Log Anthropic Messages bodies, forward to CCR")
    parser.add_argument("--listen", default="127.0.0.1:3457")
    parser.add_argument("--upstream", default="127.0.0.1:3456")
    parser.add_argument(
        "--log-dir",
        default=str(Path.home() / ".claude" / "prompt-enrichment" / "prompt-logs"),
    )
    args = parser.parse_args()
    listen_host, listen_port = _split_upstream(args.listen if ":" in args.listen else f"127.0.0.1:{args.listen}")
    upstream = _split_upstream(args.upstream)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    server = PromptLogServer((listen_host, listen_port), upstream, log_dir)
    sys.stderr.write(f"prompt-log-proxy listen={listen_host}:{listen_port} upstream={upstream[0]}:{upstream[1]} logs={log_dir}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
