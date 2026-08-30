from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import PRODUCT, secrets_path


class PathsTests(unittest.TestCase):
    def test_given_product_when_default_then_dev_conductor_not_mac_ai_setup(self) -> None:
        self.assertEqual(PRODUCT, "dev-conductor")
        self.assertIn("dev-conductor", str(secrets_path()))
        self.assertNotIn("mac-ai-setup", str(secrets_path()))
