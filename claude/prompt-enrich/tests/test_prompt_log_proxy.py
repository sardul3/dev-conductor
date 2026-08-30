#!/usr/bin/env python3
"""Proxy logs POST /v1/messages then forwards to an upstream."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prompt_log_proxy import PromptLogServer  # noqa: E402


class _FakeUpstream(BaseHTTPRequestHandler):
    last_body = b""

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length") or 0)
        _FakeUpstream.last_body = self.rfile.read(n)
        payload = b'{"id":"ok","content":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args: object) -> None:
        return


class PromptLogProxyTests(unittest.TestCase):
    def test_logs_and_forwards_messages(self) -> None:
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), _FakeUpstream)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        up_port = upstream.server_address[1]
        body = {
            "model": "test",
            "system": "You are Claude Code bloated system",
            "tools": [{"name": "Bash", "input_schema": {"type": "object"}}],
            "messages": [{"role": "user", "content": "hello"}],
        }
        raw = json.dumps(body).encode()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                proxy = PromptLogServer(
                    ("127.0.0.1", 0),
                    ("127.0.0.1", up_port),
                    Path(tmp),
                    timeout=5.0,
                )
                threading.Thread(target=proxy.serve_forever, daemon=True).start()
                pport = proxy.server_address[1]
                try:
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{pport}/v1/messages",
                        data=raw,
                        method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        self.assertEqual(200, resp.status)
                    self.assertEqual(raw, _FakeUpstream.last_body)
                    jsonl = list(Path(tmp).glob("*.jsonl"))
                    self.assertEqual(1, len(jsonl))
                    row = json.loads(jsonl[0].read_text(encoding="utf-8").splitlines()[0])
                    self.assertGreater(row["system_chars"], 10)
                    self.assertEqual(["Bash"], row["tool_names"])
                    dumped = json.loads(Path(row["raw"]).read_text(encoding="utf-8"))
                    self.assertIn("bloated system", dumped["system"])
                finally:
                    proxy.shutdown()
                    proxy.server_close()
        finally:
            upstream.shutdown()
            upstream.server_close()


if __name__ == "__main__":
    unittest.main()
