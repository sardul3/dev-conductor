from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig, RuntimeCfg
from conductor import wait_session_done
from step import StepPlan, consume_done, plan_step

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "dev-loop-test",
    "GIT_AUTHOR_EMAIL": "dev-loop-test@example.com",
    "GIT_COMMITTER_NAME": "dev-loop-test",
    "GIT_COMMITTER_EMAIL": "dev-loop-test@example.com",
}


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    (path / "README").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    return path


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


class ApproveSpecTests(unittest.TestCase):
    def test_given_spec_md_when_approve_then_writes_spec_approved_only(self) -> None:
        from conductor import approve_spec, spec_is_approved

        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "spec.md").write_text("# LCN-2\n", encoding="utf-8")
            approve_spec(run, "LCN-2")
            self.assertTrue(spec_is_approved(run))
            self.assertTrue((run / "SPEC_APPROVED").is_file())
            self.assertFalse((run / "STAGE_DONE").is_file())
            self.assertFalse((run / "SESSION_DONE").is_file())

    def test_given_no_spec_md_when_approve_then_raises(self) -> None:
        from conductor import approve_spec

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                approve_spec(Path(td), "LCN-2")

    def test_given_already_approved_when_approve_then_idempotent(self) -> None:
        from conductor import approve_spec, spec_is_approved

        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "spec.md").write_text("# LCN-2\n", encoding="utf-8")
            approve_spec(run, "LCN-2")
            approve_spec(run, "LCN-2")
            self.assertTrue(spec_is_approved(run))
            self.assertFalse((run / "STAGE_DONE").is_file())


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

    def test_given_writer_ok_and_lease_when_step_then_verify_cwd_is_worktree(self) -> None:
        from paths import run_dir
        from step import step

        cfg = _cfg()
        cfg.git.require_github_remote = False
        cfg.git.allow_outside_dev = True
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = _git_repo(root / "langchain")
            worktree = _git_repo(root / "langchain-worktrees" / "LCN-2")
            os.environ["DEVLOOP_HOME"] = str(root)
            seen: list[Path] = []

            def fake_verify(repo: Path, _cfg: DevLoopConfig, log_path: Path | None = None) -> int:
                seen.append(Path(repo).resolve())
                if log_path:
                    log_path.write_text(f"cwd {repo}\n", encoding="utf-8")
                return 0

            try:
                run = run_dir("LCN-2")
                (run / "SPEC_APPROVED").write_text("yes\n", encoding="utf-8")
                (run / "spec.md").write_text("# LCN-2\n", encoding="utf-8")
                (run / "baseline.json").write_text("{}\n", encoding="utf-8")
                (run / "lease.json").write_text(
                    json.dumps(
                        {
                            "kind": "worktree",
                            "path": str(worktree),
                            "origin": str(origin),
                            "branch": "main",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (run / "status.json").write_text(
                    json.dumps(
                        {
                            "ticket": "LCN-2",
                            "history": [
                                {"stage": "test_writer", "status": "ok"},
                                {"stage": "writer", "status": "ok"},
                            ],
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                with patch("verify_infer.run_verify", fake_verify):
                    rc = step("LCN-2", origin, cfg)
                self.assertEqual(rc, 0)
                self.assertEqual(seen, [worktree.resolve()])
                self.assertNotEqual(seen[0], origin.resolve())
                self.assertNotEqual(seen[0], Path.cwd().resolve())
            finally:
                os.environ.pop("DEVLOOP_HOME", None)
