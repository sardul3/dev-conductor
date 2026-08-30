from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from conventional import is_conventional, rewrite_subject

class ConventionalTests(unittest.TestCase):
    def test_given_feat_subject_when_check_then_true(self) -> None:
        self.assertTrue(is_conventional("feat: add health (LAB-1)"))

    def test_given_wip_when_check_then_false(self) -> None:
        self.assertFalse(is_conventional("wip stuff"))

    def test_given_plain_when_rewrite_then_feat_and_key(self) -> None:
        self.assertEqual(
            rewrite_subject("Add health check", key="LAB-1", commit_type="feat"),
            "feat: Add health check (LAB-1)",
        )
