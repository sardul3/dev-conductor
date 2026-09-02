from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import (
    VisualEvidenceMissing,
    capture_http,
    comment_visual_evidence,
    list_visual_evidence,
    render_http_markdown,
    require_visual_evidence,
    visual_markdown,
)


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


class VisualEvidenceTests(unittest.TestCase):
    def test_given_png_when_list_visual_then_finds_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            ev = run / "evidence"
            ev.mkdir()
            (ev / "tests.png").write_bytes(b"\x89PNG\r\n")
            (ev / "notes.txt").write_text("not visual\n", encoding="utf-8")
            files = list_visual_evidence(run)
            self.assertEqual([p.name for p in files], ["tests.png"])

    def test_given_require_visual_when_missing_then_raises(self) -> None:
        from config import DevLoopConfig, EvidenceCfg

        cfg = DevLoopConfig(evidence=EvidenceCfg(require_visual=True))
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            with self.assertRaises(VisualEvidenceMissing) as ctx:
                require_visual_evidence(cfg, run)
            msg = str(ctx.exception)
            self.assertIn("evidence", msg.lower())
            self.assertIn(str(run / "evidence"), msg)
            self.assertIn("step again", msg.lower())

    def test_given_require_visual_when_png_then_ok(self) -> None:
        from config import DevLoopConfig, EvidenceCfg

        cfg = DevLoopConfig(evidence=EvidenceCfg(require_visual=True))
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            ev = run / "evidence"
            ev.mkdir()
            png = ev / "run.png"
            png.write_bytes(b"\x89PNG\r\n")
            files = require_visual_evidence(cfg, run)
            self.assertEqual(files, [png])

    def test_given_require_visual_off_when_missing_then_empty(self) -> None:
        from config import DevLoopConfig, EvidenceCfg

        cfg = DevLoopConfig(evidence=EvidenceCfg(require_visual=False))
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(require_visual_evidence(cfg, Path(td)), [])

    def test_given_files_when_visual_markdown_then_image_links(self) -> None:
        md = visual_markdown([Path("/tmp/tests.png"), Path("/tmp/curl.webp")])
        self.assertIn("![tests](tests.png)", md)
        self.assertIn("![curl](curl.webp)", md)

    def test_given_files_when_comment_visual_then_gh_attach(self) -> None:
        from unittest.mock import patch

        with patch("evidence.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = ""
            run.return_value.stderr = ""
            png = Path("/tmp/tests.png")
            comment_visual_evidence(Path("/tmp/repo"), 7, [png], gh_bin="gh")
            cmd = run.call_args[0][0]
            self.assertIn("pr", cmd)
            self.assertIn("comment", cmd)
            self.assertIn("--attach", cmd)
            self.assertTrue(any(str(png) == str(x) for x in cmd))
