from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import capture_http, render_http_markdown


class FakeResp:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class EvidenceTests(unittest.TestCase):
    def test_given_probe_when_capture_then_markdown_has_status_and_body(self) -> None:
        captured: list[Request] = []

        def urlopen(req: Request, timeout: int = 0) -> FakeResp:
            captured.append(req)
            return FakeResp(json.dumps({"status": "ok"}).encode(), status=200)

        probes = [{"method": "GET", "url": "http://127.0.0.1:9/health"}]
        md = capture_http(probes, urlopen=urlopen, timeout=1)
        self.assertIn("GET http://127.0.0.1:9/health", md)
        self.assertIn("200", md)
        self.assertIn('"status": "ok"', md)
        self.assertTrue(captured)

    def test_given_render_when_error_then_records_failure(self) -> None:
        md = render_http_markdown("POST", "http://x/y", 500, '{"err":true}', error=None)
        self.assertIn("POST http://x/y", md)
        self.assertIn("500", md)
