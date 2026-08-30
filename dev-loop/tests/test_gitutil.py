from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gitutil import denylisted, github_remote, is_git_repo, under_dev


class GitutilTests(unittest.TestCase):
    def test_given_github_remote_when_github_remote_then_url(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(
                ["git", "remote", "add", "origin", "git@github.com:sardul3/app.git"],
                cwd=repo,
            )
            self.assertTrue(is_git_repo(repo))
            self.assertIn("github.com", github_remote(repo) or "")

    def test_given_denylist_name_when_denylisted_then_true(self) -> None:
        self.assertTrue(denylisted(Path("/x/claude-proxy"), ["claude-proxy"]))
        self.assertFalse(denylisted(Path("/x/app"), []))

    def test_under_dev(self) -> None:
        root = Path("/Users/me/dev")
        self.assertTrue(under_dev(Path("/Users/me/dev/app"), root))
        self.assertFalse(under_dev(Path("/tmp/app"), root))
