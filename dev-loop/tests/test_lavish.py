from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig, load_config
from lavish import decide_lavish, is_ui_repo


class LavishTests(unittest.TestCase):
    def test_given_react_package_when_detect_then_ui(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "package.json").write_text(
                json.dumps({"dependencies": {"react": "19.0.0"}}),
                encoding="utf-8",
            )
            self.assertTrue(is_ui_repo(repo))

    def test_given_java_only_when_detect_then_not_ui(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
            self.assertFalse(is_ui_repo(repo))

    def test_given_auto_and_ui_repo_when_decide_then_on(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "components.json").write_text("{}", encoding="utf-8")
            cfg = DevLoopConfig()
            cfg.lavish.enabled = "auto"
            d = decide_lavish(cfg, repo)
            self.assertTrue(d.enabled)
            self.assertIn("auto", d.reason)

    def test_given_auto_and_api_repo_when_decide_then_off(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "go.mod").write_text("module x", encoding="utf-8")
            cfg = DevLoopConfig()
            cfg.lavish.enabled = "auto"
            d = decide_lavish(cfg, repo)
            self.assertFalse(d.enabled)

    def test_given_off_when_ui_repo_then_still_off(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "components.json").write_text("{}", encoding="utf-8")
            cfg = DevLoopConfig()
            cfg.lavish.enabled = "off"
            self.assertFalse(decide_lavish(cfg, repo).enabled)

    def test_given_on_when_api_repo_then_on(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            cfg = DevLoopConfig()
            cfg.lavish.enabled = "on"
            self.assertTrue(decide_lavish(cfg, repo).enabled)

    def test_given_repo_override_when_auto_then_honors_slug(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "payments-api"
            repo.mkdir()
            (repo / "components.json").write_text("{}", encoding="utf-8")
            cfg = DevLoopConfig()
            cfg.lavish.enabled = "auto"
            cfg.lavish.repos = {"payments-api": "off"}
            self.assertFalse(decide_lavish(cfg, repo).enabled)

    def test_given_example_when_load_then_lavish_auto(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.yaml.example")
        self.assertEqual(cfg.lavish.enabled, "auto")

    def test_given_test_profile_when_load_then_lavish_off(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.test.yaml")
        self.assertEqual(cfg.lavish.enabled, "off")


if __name__ == "__main__":
    unittest.main()
