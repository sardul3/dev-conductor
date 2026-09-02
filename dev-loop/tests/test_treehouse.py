from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig, load_config
from progress import record
from treehouse import (
    acquire_lease,
    count_active_runs,
    prepare_workspace,
    release_lease,
    workspace_for_ticket,
    workspace_notice,
    worktree_path,
)



import os
import subprocess

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "dev-loop-test",
    "GIT_AUTHOR_EMAIL": "dev-loop-test@example.com",
    "GIT_COMMITTER_NAME": "dev-loop-test",
    "GIT_COMMITTER_EMAIL": "dev-loop-test@example.com",
}


def _init_origin(root: Path) -> Path:
    origin = root / "origin"
    origin.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(origin)], check=True, capture_output=True)
    (origin / "README").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(origin), "add", "README"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(origin), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    return origin


class _Proc:
    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class FakeTreehouse:
    def __init__(self, path: str = "/tmp/leased-wt") -> None:
        self.path = path
        self.lease_id = "lease-abc"
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, cmd, **kwargs):  # noqa: ANN001, ANN003
        argv = [str(x) for x in cmd]
        cwd = kwargs.get("cwd")
        self.calls.append((argv, str(cwd) if cwd is not None else None))
        if "get" in argv:
            payload = {
                "path": self.path,
                "lease_id": self.lease_id,
                "lease_holder": "dev-loop",
                "leased_at": "2026-08-30T00:00:00Z",
                "base_branch": "main",
            }
            return _Proc(stdout=json.dumps(payload) + "\n")
        if "return" in argv:
            return _Proc()
        return _Proc(returncode=1, stderr="unexpected")


class TreehouseTests(unittest.TestCase):
    def test_given_lease_json_when_acquire_then_returns_path_and_id(self) -> None:
        fake = FakeTreehouse("/tmp/wt-1")
        lease = acquire_lease(Path("/tmp/origin"), bin="treehouse", holder="dev-loop:ASE-1", runner=fake)
        self.assertEqual(lease.path, Path("/tmp/wt-1"))
        self.assertEqual(lease.lease_id, "lease-abc")
        argv, cwd = fake.calls[0]
        self.assertIn("--lease", argv)
        self.assertIn("--json", argv)
        self.assertEqual(cwd, "/tmp/origin")

    def test_given_missing_binary_when_acquire_then_exits_with_install_hint(self) -> None:
        def boom(*_a, **_k):  # noqa: ANN002, ANN003
            raise FileNotFoundError("treehouse")

        with self.assertRaises(SystemExit) as ctx:
            acquire_lease(Path("/tmp/origin"), runner=boom)
        self.assertIn("treehouse", str(ctx.exception).lower())
        self.assertIn("install", str(ctx.exception).lower())

    def test_given_three_active_runs_when_prepare_fourth_then_exits(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs = Path(td)
            for key in ("ASE-1", "ASE-2", "ASE-3"):
                run = runs / key
                run.mkdir()
                record(run, "spec", "waiting_approval", ticket=key)
            cfg = DevLoopConfig()
            cfg.git.isolation = "none"
            cfg.queue.max_active = 3
            fourth = runs / "ASE-4"
            fourth.mkdir()
            with self.assertRaises(SystemExit) as ctx:
                prepare_workspace(Path("/tmp/origin"), cfg, fourth, runs_root=runs, runner=FakeTreehouse())
            self.assertIn("max_active", str(ctx.exception))

    def test_given_shipped_run_when_count_then_slot_is_free(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs = Path(td)
            done = runs / "ASE-1"
            done.mkdir()
            record(done, "ship", "pr", ticket="ASE-1")
            waiting = runs / "ASE-2"
            waiting.mkdir()
            record(waiting, "spec", "waiting_approval", ticket="ASE-2")
            self.assertEqual(count_active_runs(runs), 1)

    def test_given_treehouse_isolation_when_prepare_then_writes_lease_and_uses_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "ASE-9"
            run.mkdir()
            cfg = DevLoopConfig()
            cfg.git.isolation = "treehouse"
            cfg.queue.max_active = 3
            fake = FakeTreehouse("/tmp/leased-ase-9")
            workspace = prepare_workspace(Path("/tmp/origin"), cfg, run, runs_root=Path(td), runner=fake)
            self.assertEqual(workspace, Path("/tmp/leased-ase-9"))
            data = json.loads((run / "lease.json").read_text(encoding="utf-8"))
            self.assertEqual(data["path"], "/tmp/leased-ase-9")
            self.assertEqual(data["lease_id"], "lease-abc")
            self.assertEqual(data["origin"], "/tmp/origin")

    def test_given_lease_when_release_then_calls_treehouse_return(self) -> None:
        fake = FakeTreehouse()
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            (run / "lease.json").write_text(
                json.dumps(
                    {
                        "path": "/tmp/leased-wt",
                        "lease_id": "lease-abc",
                        "origin": "/tmp/origin",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cfg = DevLoopConfig()
            cfg.git.isolation = "treehouse"
            release_lease(run, cfg, runner=fake)
            argv, _cwd = fake.calls[0]
            self.assertIn("return", argv)
            self.assertIn("/tmp/leased-wt", argv)
            self.assertIn("--force", argv)
            self.assertIn("lease-abc", argv)

    def test_given_example_defaults_when_load_then_worktree_and_max_active_three(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.yaml.example")
        self.assertEqual(cfg.git.isolation, "worktree")
        self.assertEqual(cfg.queue.max_active, 3)

    def test_given_test_profile_when_load_then_isolation_none(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.test.yaml")
        self.assertEqual(cfg.git.isolation, "none")
        self.assertEqual(cfg.queue.max_active, 3)


    def test_given_origin_when_worktree_path_then_sibling_dir_has_no_leading_dot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "langchain"
            origin.mkdir()
            dest = worktree_path(origin, "LCN-2")
            self.assertEqual(dest.name, "LCN-2")
            self.assertEqual(dest.parent.name, "langchain-worktrees")
            self.assertFalse(dest.parent.name.startswith("."))
            self.assertEqual(dest.parent.parent, origin.resolve().parent)

    def test_given_worktree_isolation_when_prepare_then_adds_detached_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = _init_origin(root)
            run = root / "runs" / "ASE-9"
            run.mkdir(parents=True)
            cfg = DevLoopConfig()
            cfg.git.isolation = "worktree"
            cfg.queue.max_active = 3
            workspace = prepare_workspace(origin, cfg, run, runs_root=root / "runs")
            expected = worktree_path(origin, "ASE-9")
            self.assertEqual(workspace, expected)
            self.assertTrue(workspace.is_dir())
            data = json.loads((run / "lease.json").read_text(encoding="utf-8"))
            self.assertEqual(data["kind"], "worktree")
            self.assertEqual(data["path"], str(expected))
            self.assertEqual(data["origin"], str(origin.resolve()))
            listed = subprocess.run(
                ["git", "-C", str(origin), "worktree", "list", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn(str(expected), listed)

    def test_given_worktree_lease_when_release_then_removes_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = _init_origin(root)
            run = root / "runs" / "ASE-9"
            run.mkdir(parents=True)
            cfg = DevLoopConfig()
            cfg.git.isolation = "worktree"
            cfg.queue.max_active = 3
            workspace = prepare_workspace(origin, cfg, run, runs_root=root / "runs")
            self.assertTrue(workspace.exists())
            release_lease(run, cfg)
            self.assertFalse(workspace.exists())
            listed = subprocess.run(
                ["git", "-C", str(origin), "worktree", "list", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn("ASE-9", listed)

    def test_given_path_when_workspace_notice_then_unambiguous_line(self) -> None:
        line = workspace_notice(Path("/tmp/langchain-worktrees/LCN-2"))
        self.assertEqual(line, "dev-loop: workspace /tmp/langchain-worktrees/LCN-2")

    def test_given_legacy_dotted_lease_when_prepare_then_reuses_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = _init_origin(root)
            run = root / "runs" / "ASE-9"
            run.mkdir(parents=True)
            legacy = origin.parent / f".{origin.name}-worktrees" / "ASE-9"
            legacy.parent.mkdir(parents=True)
            subprocess.run(
                ["git", "-C", str(origin), "worktree", "add", "--detach", str(legacy), "main"],
                check=True,
                capture_output=True,
            )
            (run / "lease.json").write_text(
                json.dumps(
                    {
                        "kind": "worktree",
                        "path": str(legacy),
                        "origin": str(origin.resolve()),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cfg = DevLoopConfig()
            cfg.git.isolation = "worktree"
            cfg.queue.max_active = 3
            workspace = prepare_workspace(origin, cfg, run, runs_root=root / "runs")
            self.assertEqual(workspace, legacy)
            self.assertFalse(worktree_path(origin, "ASE-9").exists())

    def test_given_existing_worktree_when_prepare_then_reuses_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = _init_origin(root)
            run = root / "runs" / "ASE-9"
            run.mkdir(parents=True)
            cfg = DevLoopConfig()
            cfg.git.isolation = "worktree"
            first = prepare_workspace(origin, cfg, run, runs_root=root / "runs")
            (first / "scratch.txt").write_text("keep\n", encoding="utf-8")
            second = prepare_workspace(origin, cfg, run, runs_root=root / "runs")
            self.assertEqual(first, second)
            self.assertEqual((second / "scratch.txt").read_text(encoding="utf-8"), "keep\n")

    def test_given_lease_when_workspace_for_ticket_then_prefers_worktree_not_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = root / "langchain"
            worktree = root / "langchain-worktrees" / "LCN-2"
            origin.mkdir()
            worktree.mkdir(parents=True)
            run = root / "runs" / "LCN-2"
            run.mkdir(parents=True)
            (run / "lease.json").write_text(
                json.dumps({"kind": "worktree", "path": str(worktree), "origin": str(origin)}) + "\n",
                encoding="utf-8",
            )
            os.environ["DEVLOOP_HOME"] = str(root)
            try:
                got = workspace_for_ticket(
                    "LCN-2",
                    Path("/tmp/not-the-worktree"),
                    {"origin_repo": str(origin), "repo": str(origin)},
                )
                self.assertEqual(got.resolve(), worktree.resolve())
                self.assertNotEqual(got.resolve(), Path.cwd().resolve())
            finally:
                os.environ.pop("DEVLOOP_HOME", None)


if __name__ == "__main__":
    unittest.main()
