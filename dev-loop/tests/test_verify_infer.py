from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig
from verify_infer import infer_recipe


class VerifyInferTests(unittest.TestCase):
    def test_given_gradlew_when_infer_then_uses_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            (repo / "build.gradle").write_text("", encoding="utf-8")
            r = infer_recipe(repo, DevLoopConfig())
            self.assertIsNotNone(r)
            assert r
            self.assertEqual(r.test[0], str((repo / "gradlew").resolve()))
            self.assertIn("test", r.test)

    def test_given_no_markers_when_infer_then_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "notes.txt").write_text("x", encoding="utf-8")
            self.assertIsNone(infer_recipe(repo, DevLoopConfig()))

    def test_given_override_when_infer_then_uses_config_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "svc"
            repo.mkdir()
            cfg = DevLoopConfig(verify={"svc": {"test": "true"}}, health={"svc": "http://127.0.0.1/health"})
            r = infer_recipe(repo, cfg)
            assert r
            self.assertEqual(r.test, ["true"])
            self.assertEqual(r.health, "http://127.0.0.1/health")
