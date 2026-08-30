#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from after_launch import is_launch  # noqa: E402


class AfterLaunchTests(unittest.TestCase):
    def test_given_launch_script_when_bash_then_true(self) -> None:
        self.assertTrue(
            is_launch(
                {
                    "tool_name": "Bash",
                    "tool_input": {
                        "command": "bash ~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file /tmp/x.md"
                    },
                }
            )
        )

    def test_given_other_bash_when_check_then_false(self) -> None:
        self.assertFalse(
            is_launch({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        )
        self.assertFalse(is_launch({"tool_name": "Write", "tool_input": {}}))


if __name__ == "__main__":
    unittest.main()
