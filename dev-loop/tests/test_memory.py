from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import memory
from memory import fingerprint, index_is_fresh, regenerate


def _git_init(root: Path) -> None:
    subprocess.check_call(["git", "init"], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t.com"], cwd=root)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=root)
    (root / "README.md").write_text("hi\n", encoding="utf-8")
    (root / "src" / "main" / "java").mkdir(parents=True)
    (root / "src" / "main" / "java" / "FooController.java").write_text(
        "class FooController { }\n", encoding="utf-8"
    )
    subprocess.check_call(["git", "add", "-A"], cwd=root)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL)


class MemoryTests(unittest.TestCase):
    def test_given_unchanged_repo_when_index_then_skips_regenerate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "app"
            repo.mkdir()
            _git_init(repo)
            mem_root = Path(td) / "memhome"
            orig = memory.memory_dir

            def fake_memory_dir(slug: str) -> Path:
                p = mem_root / slug
                p.mkdir(parents=True, exist_ok=True)
                return p

            memory.memory_dir = fake_memory_dir  # type: ignore[assignment]
            try:
                regenerate(repo)
                fp1 = fingerprint(repo)
                self.assertTrue(index_is_fresh(repo))
                (repo / "README.md").write_text("changed\n", encoding="utf-8")
                subprocess.check_call(["git", "add", "README.md"], cwd=repo)
                subprocess.check_call(["git", "commit", "-m", "c"], cwd=repo, stdout=subprocess.DEVNULL)
                self.assertNotEqual(fp1, fingerprint(repo))
                self.assertFalse(index_is_fresh(repo))
            finally:
                memory.memory_dir = orig  # type: ignore[assignment]
