from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from touched import changed_since, snapshot_tree


class TouchedTests(unittest.TestCase):
    def test_given_unrelated_dirty_when_writer_edits_then_only_new_hash_is_touched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "keep.txt").write_text("a\n", encoding="utf-8")
            (repo / "work.txt").write_text("b\n", encoding="utf-8")
            base = snapshot_tree(repo)
            (repo / "work.txt").write_text("b2\n", encoding="utf-8")
            (repo / "new.txt").write_text("n\n", encoding="utf-8")
            changed = changed_since(repo, base)
            self.assertIn("work.txt", changed)
            self.assertIn("new.txt", changed)
            self.assertNotIn("keep.txt", changed)
