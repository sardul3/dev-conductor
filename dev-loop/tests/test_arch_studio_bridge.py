from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arch_studio_bridge import (
    approve_arch,
    arch_review_required,
    decide_arch_studio,
    reject_arch,
    review_html,
    write_manifest,
)
from config import DevLoopConfig


class ArchStudioBridgeTests(unittest.TestCase):
    def test_given_integration_label_when_auto_then_enabled(self) -> None:
        cfg = DevLoopConfig()
        cfg.arch_studio.enabled = "auto"
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            issue = {"summary": "Ship it", "labels": ["integration"], "description": ""}
            decision = decide_arch_studio(cfg, repo, issue)
            self.assertTrue(decision.enabled)
            self.assertTrue(decision.require_review)

    def test_given_plain_bug_when_auto_then_off(self) -> None:
        cfg = DevLoopConfig()
        cfg.arch_studio.enabled = "auto"
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            issue = {"summary": "Fix typo in README", "labels": [], "description": ""}
            self.assertFalse(decide_arch_studio(cfg, repo, issue).enabled)

    def test_given_require_review_when_approve_arch_then_writes_handshake(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            out = run / "architecture"
            out.mkdir()
            review_html(run).write_text("<html></html>", encoding="utf-8")
            write_manifest(
                run,
                decide_arch_studio(DevLoopConfig(), run, {"summary": "integration"}),
            )
            approve_arch(run, "LCN-9")
            self.assertTrue((run / "ARCH_APPROVED").is_file())
            self.assertTrue(arch_review_required(run))

    def test_given_reject_when_approved_then_clears_handshake(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            out = run / "architecture"
            out.mkdir()
            review_html(run).write_text("<html></html>", encoding="utf-8")
            approve_arch(run, "LCN-9")
            reject_arch(run, "LCN-9", note="missing trust view")
            self.assertFalse((run / "ARCH_APPROVED").is_file())
            payload = json.loads((out / "review-decisions.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_disposition"], "rejected")

    def test_given_arch_required_when_approve_spec_without_arch_then_raises(self) -> None:
        from conductor import approve_spec

        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "spec.md").write_text("# spec\n", encoding="utf-8")
            write_manifest(
                run,
                decide_arch_studio(DevLoopConfig(), run, {"summary": "Azure integration"}),
            )
            with self.assertRaises(FileNotFoundError):
                approve_spec(run, "LCN-9")
