from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from budget import (  # noqa: E402
    BudgetExhausted,
    approx_tokens,
    check_and_charge,
    check_budget,
    remaining_session_usd,
)
from config import DevLoopConfig, load_config  # noqa: E402
from conductor import launch_prompt  # noqa: E402


def _cfg(**caps) -> DevLoopConfig:
    cfg = DevLoopConfig()
    cfg.runtime.no_launch = False
    cfg.runtime.agent = "claude"
    cfg.runtime.launch_script = "/nonexistent/launch.sh"
    for key, val in caps.items():
        setattr(cfg.caps, key, val)
    return cfg


class BudgetTests(unittest.TestCase):
    def test_given_zero_caps_when_check_then_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            ok, reason = check_budget(_cfg(), run)
            self.assertTrue(ok)
            self.assertEqual(reason, "unlimited")

    def test_given_max_launches_when_at_cap_then_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            cfg = _cfg(max_launches=2)
            check_and_charge(cfg, run, prompt="a" * 40, name="a")
            check_and_charge(cfg, run, prompt="b" * 40, name="b")
            ok, reason = check_budget(cfg, run)
            self.assertFalse(ok)
            self.assertIn("launches", reason)

    def test_given_max_tokens_when_over_then_charge_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            cfg = _cfg(max_tokens=20)
            prompt = "x" * 80  # 20 tokens
            check_and_charge(cfg, run, prompt=prompt, name="one")
            with self.assertRaises(BudgetExhausted) as ctx:
                check_and_charge(cfg, run, prompt=prompt, name="two")
            self.assertIn("tokens", str(ctx.exception))

    def test_given_wall_sec_when_expired_then_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            cfg = _cfg(wall_sec=60)
            start = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
            check_and_charge(cfg, run, prompt="hi", name="a", now=start)
            later = start + timedelta(seconds=61)
            ok, reason = check_budget(cfg, run, now=later)
            self.assertFalse(ok)
            self.assertIn("wall", reason)

    def test_given_budget_usd_when_remaining_then_session_cap(self) -> None:
        cfg = _cfg(max_budget_usd=2.5)
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            self.assertEqual(remaining_session_usd(cfg, run), 2.5)
            self.assertIsNone(remaining_session_usd(_cfg(max_budget_usd=0), run))

    def test_given_approx_tokens_when_prompt_then_chars_div_four(self) -> None:
        self.assertEqual(approx_tokens("abcd"), 1)
        self.assertEqual(approx_tokens(""), 1)

    def test_given_example_when_load_then_run_caps_default_off(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.yaml.example")
        self.assertEqual(cfg.caps.max_launches, 0)
        self.assertEqual(cfg.caps.max_tokens, 0)
        self.assertEqual(cfg.caps.max_budget_usd, 0.0)
        self.assertEqual(cfg.caps.wall_sec, 0)

    def test_given_at_launch_cap_when_launch_prompt_then_raises_and_skips_popen(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            repo = Path(td) / "repo"
            repo.mkdir()
            cfg = _cfg(max_launches=1)
            check_and_charge(cfg, run, prompt="first", name="seed")
            with patch("conductor.subprocess.Popen") as popen:
                with self.assertRaises(BudgetExhausted):
                    launch_prompt("second session", repo, run, "writer-1", cfg)
                popen.assert_not_called()
            self.assertTrue((run / "STOPPED").is_file())
            data = json.loads((run / "budget.json").read_text(encoding="utf-8"))
            self.assertEqual(data["launches"], 1)


if __name__ == "__main__":
    unittest.main()
