from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from ship import branch_name, conventional_message, create_pr, slugify


class ShipTests(unittest.TestCase):
    def test_given_summary_when_branch_name_then_feat_key_slug(self) -> None:
        self.assertEqual(branch_name("ASE-12", "Add Health Check!"), "feat/ASE-12-add-health-check")

    def test_given_summary_when_conventional_message_then_type_and_key(self) -> None:
        msg = conventional_message("ASE-12", "Add health check", "Do actuator.")
        self.assertTrue(msg.startswith("feat: Add health check (ASE-12)"))
        self.assertIn("Do actuator.", msg)

    def test_slugify_strips_noise(self) -> None:
        self.assertEqual(slugify("Hello, World!!"), "hello-world")

    def test_given_base_when_create_pr_then_passes_flag(self) -> None:
        with patch("ship.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "https://github.com/org/repo/pull/12\n"
            run.return_value.stderr = ""
            n = create_pr(Path("/tmp"), "feat: x (A-1)", "body", base="feat/A-1")
            self.assertEqual(n, 12)
            cmd = run.call_args[0][0]
            self.assertIn("--base", cmd)
            self.assertIn("feat/A-1", cmd)

    def test_given_only_untracked_when_commit_then_skips(self) -> None:
        import subprocess
        import tempfile
        from ship import commit_if_needed
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init", "-q"], cwd=td)
            subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=td)
            subprocess.check_call(["git", "config", "user.name", "t"], cwd=td)
            (repo / "keep.txt").write_text("a\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "keep.txt"], cwd=td)
            subprocess.check_call(["git", "commit", "-qm", "init"], cwd=td)
            (repo / "noise.txt").write_text("x\n", encoding="utf-8")
            self.assertFalse(commit_if_needed(repo, "feat: no (A-1)\n"))
