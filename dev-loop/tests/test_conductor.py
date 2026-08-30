from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conductor import require_key


class ConductorTests(unittest.TestCase):
    def test_given_bad_key_when_require_key_then_exits(self) -> None:
        with self.assertRaises(SystemExit):
            require_key("not-a-key")

    def test_given_key_when_require_key_then_uppercases(self) -> None:
        self.assertEqual(require_key("ase-12"), "ASE-12")
