from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pick import CREATE_ID, init_local_repo, list_candidates


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


class PickTests(unittest.TestCase):
    def test_given_tree_when_list_then_git_and_folders_to_max_depth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            git = _mkdir(root / "app")
            subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=git)
            _mkdir(root / "app" / "src")
            _mkdir(root / "scratch")
            _mkdir(root / "scratch" / "nested")
            _mkdir(root / "scratch" / "nested" / "deep")
            _mkdir(root / "node_modules" / "pkg")
            cands = list_candidates(root, max_depth=2, skip=["node_modules"], denylist=[], allowlist=[], max_choices=40)
            rels = {c["rel"] for c in cands}
            self.assertIn("app", rels)
            self.assertIn("scratch", rels)
            self.assertIn("scratch/nested", rels)
            self.assertNotIn("scratch/nested/deep", rels)
            self.assertFalse(any(r.startswith("node_modules") for r in rels))
            kinds = {c["rel"]: c["kind"] for c in cands}
            self.assertEqual(kinds["app"], "git")
            self.assertEqual(kinds["scratch"], "folder")

    def test_given_denylist_when_list_then_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mkdir(root / "keep")
            _mkdir(root / "secret-lab")
            cands = list_candidates(root, max_depth=1, skip=[], denylist=["secret-lab"], allowlist=[], max_choices=40)
            self.assertEqual([c["rel"] for c in cands], ["keep"])

    def test_given_name_when_init_local_then_git_repo_with_readme(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = init_local_repo(Path(td), "AI Trend Agent")
            self.assertTrue((dest / ".git").exists())
            self.assertTrue((dest / "README.md").is_file())
            self.assertEqual(dest.name, "ai-trend-agent")

    def test_create_id_is_stable(self) -> None:
        self.assertEqual(CREATE_ID, "__create__")
