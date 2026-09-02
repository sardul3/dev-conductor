from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CursorInstallTests(unittest.TestCase):
    def test_given_repo_skills_when_cursor_install_then_globs_all_skill_md(self) -> None:
        text = (ROOT / "cursor" / "dev-loop" / "install.sh").read_text(encoding="utf-8")
        self.assertIn('SKILL.md', text)
        self.assertNotIn(
            "for n in dev-loop story-spec test-writer repo-memory",
            text,
        )
        skills = [p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()]
        self.assertGreaterEqual(len(skills), 20)
        self.assertIn("prompt-contract", skills)
        self.assertIn("design-tree-interview", skills)

    def test_given_existing_hooks_when_merge_then_keeps_other_commands(self) -> None:
        sys.path.insert(0, str(ROOT / "cursor" / "dev-loop"))
        from merge_hooks import merge_devloop_hooks

        data = {"version": 1, "hooks": {"sessionStart": [{"command": "echo other"}]}}
        out = merge_devloop_hooks(data, "python3 /tmp/session_start_cursor.py", "python3 /tmp/deny_read_cursor.py")
        cmds = [e["command"] for e in out["hooks"]["sessionStart"]]
        self.assertIn("echo other", cmds)
        self.assertTrue(any("session_start_cursor" in c for c in cmds))
