#!/usr/bin/env python3
"""Tests: handoff files land in the prompt-enrich runs dir, never /tmp."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from save_handoff import save_handoff  # noqa: E402


class SaveHandoffTests(unittest.TestCase):
    def test_writes_under_runs_with_skip_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = save_handoff("# Goal\nship it\n", Path(tmp), now_utc="2026-08-30T16:00:00Z")
            self.assertEqual(Path(tmp), path.parent)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!-- PROMPT_CONTRACT_V1 -->"))
            self.assertIn("ship it", text)
            self.assertTrue(path.name.startswith("handoff-"))

    def test_does_not_duplicate_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = save_handoff("<!-- PROMPT_CONTRACT_V1 -->\n# Already\n", Path(tmp), now_utc="2026-08-30T16:00:00Z")
            self.assertEqual(1, path.read_text(encoding="utf-8").count("PROMPT_CONTRACT_V1"))


if __name__ == "__main__":
    unittest.main()
