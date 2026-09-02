from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig, RuntimeCfg
from conductor import wait_session_done
from step import StepPlan, consume_done, plan_step


def _cfg() -> DevLoopConfig:
    cfg = DevLoopConfig()
    cfg.runtime = RuntimeCfg(agent="cursor", no_launch=True)
    cfg.stages_enabled = {
        "spec": True,
        "test_writer": True,
        "writer": True,
        "verify": True,
        "review": True,
        "simplify": False,
        "ship": False,
    }
    cfg.evidence.enabled = False
    return cfg


class StepPlanTests(unittest.TestCase):
    def test_given_no_spec_approval_when_plan_step_then_need_spec(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "spec.md").write_text("s", encoding="utf-8")
            plan = plan_step(run, _cfg(), launched_stage=None)
            self.assertEqual(plan, StepPlan(kind="need_spec", stage="spec"))

    def test_given_approved_when_plan_step_then_setup_test_writer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "SPEC_APPROVED").write_text("yes\n", encoding="utf-8")
            plan = plan_step(run, _cfg(), launched_stage=None)
            self.assertEqual(plan, StepPlan(kind="setup", stage="test_writer"))

    def test_given_launched_test_writer_without_done_when_plan_step_then_wait(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "SPEC_APPROVED").write_text("yes\n", encoding="utf-8")
            plan = plan_step(run, _cfg(), launched_stage="test-writer")
            self.assertEqual(plan, StepPlan(kind="wait", stage="test_writer"))

    def test_given_stage_done_when_consume_then_records_ok_and_next_is_writer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "SPEC_APPROVED").write_text("yes\n", encoding="utf-8")
            (run / "STAGE_DONE").write_text("", encoding="utf-8")
            consumed = consume_done(run, "test-writer")
            self.assertEqual(consumed, "test_writer")
            self.assertFalse((run / "STAGE_DONE").is_file())
            self.assertFalse((run / "SESSION_DONE").is_file())
            plan = plan_step(run, _cfg(), launched_stage=None)
            self.assertEqual(plan, StepPlan(kind="setup", stage="writer"))

    def test_given_same_stage_still_open_when_plan_step_twice_then_wait_not_setup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "SPEC_APPROVED").write_text("yes\n", encoding="utf-8")
            first = plan_step(run, _cfg(), launched_stage="test-writer")
            second = plan_step(run, _cfg(), launched_stage="test-writer")
            self.assertEqual(first.kind, "wait")
            self.assertEqual(second, first)


class CursorWaitTests(unittest.TestCase):
    def test_given_cursor_agent_when_wait_session_done_then_does_not_sleep(self) -> None:
        class Clock:
            def __init__(self) -> None:
                self.t = 0.0
                self.sleeps = 0

            def time(self) -> float:
                return self.t

            def sleep(self, _s: float) -> None:
                self.sleeps += 1
                self.t += float(_s)

        clock = Clock()
        cfg = DevLoopConfig(runtime=RuntimeCfg(agent="cursor", wait_timeout_sec=86400))
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            with patch("conductor.time.time", clock.time), patch("conductor.time.sleep", clock.sleep):
                ok = wait_session_done(run, cfg)
        self.assertFalse(ok)
        self.assertEqual(clock.sleeps, 0)

    def test_given_cursor_agent_and_stage_done_when_wait_then_true(self) -> None:
        cfg = DevLoopConfig(runtime=RuntimeCfg(agent="cursor"))
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "STAGE_DONE").write_text("", encoding="utf-8")
            self.assertTrue(wait_session_done(run, cfg))


class StepExecuteTests(unittest.TestCase):
    def test_given_unapproved_when_step_then_exit_2(self) -> None:
        from step import step

        cfg = _cfg()
        cfg.git.require_github_remote = False
        cfg.git.allow_outside_dev = True
        with tempfile.TemporaryDirectory() as td:
            import os
            from paths import run_dir

            os.environ["DEVLOOP_HOME"] = td
            try:
                run = run_dir("ASE-9")
                (run / "spec.md").write_text("s", encoding="utf-8")
                rc = step("ASE-9", Path(td), cfg)
                self.assertEqual(rc, 2)
            finally:
                os.environ.pop("DEVLOOP_HOME", None)
