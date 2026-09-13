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
        self.assertIn("${HOME}/.local/bin", text)
        self.assertIn("dev-loop/bin/dev-loop", text)
        self.assertIn("cursor/commands/dev-loop.md", text)
        self.assertIn("alias dl=", text)
        self.assertIn("agent: cursor", text)
        cmd = (ROOT / "cursor" / "commands" / "dev-loop.md").read_text(encoding="utf-8")
        self.assertIn("name: dev-loop", cmd)
        self.assertIn("AskQuestion", cmd)
        self.assertIn("keys --recent", cmd)
        self.assertIn("approve KEY", cmd)
        self.assertIn("move_agent_to_root", cmd)
        skill = (ROOT / "skills" / "dev-loop" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("move_agent_to_root", skill)
        self.assertIn("/browse/", skill)
        self.assertIn("Jira:", skill)
        self.assertIn("Evidence", skill)
        self.assertNotIn("## Spec (excerpt)", skill)
        self.assertIn("no spec excerpt", skill.lower())
        wrapper = ROOT / "dev-loop" / "bin" / "dev-loop"
        self.assertTrue(wrapper.is_file())

    def test_given_test_writer_skill_when_read_then_forbids_toolchain_as_subject(self) -> None:
        skill = (ROOT / "skills" / "test-writer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Forbidden as test subjects", skill)
        self.assertIn("nested test runners", skill)
        self.assertIn("Never spawn", skill)
        self.assertIn("uv run pytest", skill)
        self.assertIn("cli.py verify", skill)
        self.assertIn("__pycache__", skill)
        self.assertIn(".gitignore", skill)

    def test_given_existing_hooks_when_merge_then_keeps_other_commands(self) -> None:
        sys.path.insert(0, str(ROOT / "cursor" / "dev-loop"))
        from merge_hooks import merge_devloop_hooks

        data = {"version": 1, "hooks": {"sessionStart": [{"command": "echo other"}]}}
        out = merge_devloop_hooks(data, "python3 /tmp/session_start_cursor.py", "python3 /tmp/deny_read_cursor.py")
        cmds = [e["command"] for e in out["hooks"]["sessionStart"]]
        self.assertIn("echo other", cmds)
        self.assertTrue(any("session_start_cursor" in c for c in cmds))
