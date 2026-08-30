from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from session_start import eligible


class SessionStartTests(unittest.TestCase):
    def test_given_dev_root_cwd_when_eligible_then_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "dev"
            root.mkdir()
            cfg = SimpleNamespace(dev_root=root, denylist=[])
            self.assertTrue(eligible(root, cfg))

    def test_given_path_outside_dev_when_eligible_then_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "dev"
            root.mkdir()
            other = Path(td) / "other"
            other.mkdir()
            cfg = SimpleNamespace(dev_root=root, denylist=[])
            self.assertFalse(eligible(other, cfg))

    def test_given_empty_cache_when_cached_keys_then_miss(self) -> None:
        import json
        import os
        from session_start import cached_keys, store_keys
        with tempfile.TemporaryDirectory() as td:
            os.environ["DEVLOOP_HOME"] = td
            try:
                from paths import config_dir
                (config_dir() / "cache").mkdir(parents=True, exist_ok=True)
                (config_dir() / "cache" / "keys.json").write_text(
                    json.dumps({"ts": 9e12, "keys": []}), encoding="utf-8"
                )
                from importlib import reload
                import session_start as ss
                reload(ss)
                self.assertIsNone(ss.cached_keys(600))
                ss.store_keys([])
                # empty store must not rewrite a hit
            finally:
                os.environ.pop("DEVLOOP_HOME", None)
