#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plan_guard import should_block  # noqa: E402


class PlanGuardTests(unittest.TestCase):
    def test_blocks_plan_during_enrich(self) -> None:
        self.assertTrue(should_block({"tool_name": "EnterPlanMode"}, "enriching"))

    def test_allows_after_done(self) -> None:
        self.assertFalse(should_block({"tool_name": "EnterPlanMode"}, "done"))
        self.assertFalse(should_block({"tool_name": "Write"}, "done"))

    def test_allows_bash_during_grill(self) -> None:
        self.assertFalse(should_block({"tool_name": "Bash"}, "enriching"))

    def test_blocks_explore_agent_during_enrich(self) -> None:
        self.assertTrue(should_block({"tool_name": "Agent"}, "enriching"))
        self.assertTrue(should_block({"tool_name": "Task"}, "grilling"))
        self.assertTrue(should_block({"tool_name": "Glob"}, "enriching"))
        self.assertTrue(should_block({"tool_name": "Grep"}, "enriching"))
        self.assertTrue(should_block({"tool_name": "Write"}, "enriching"))

    def test_blocks_implement_after_handoff(self) -> None:
        self.assertTrue(should_block({"tool_name": "Write"}, "handed_off"))
        self.assertTrue(should_block({"tool_name": "Edit"}, "handed_off"))
        self.assertTrue(should_block({"tool_name": "Bash"}, "handed_off"))
        self.assertTrue(should_block({"tool_name": "Agent"}, "handed_off"))
        self.assertFalse(should_block({"tool_name": "Read"}, "handed_off"))
        self.assertFalse(should_block({"tool_name": "AskUserQuestion"}, "handed_off"))

    def test_allows_read_and_questions(self) -> None:
        self.assertFalse(should_block({"tool_name": "Read"}, "enriching"))
        self.assertFalse(should_block({"tool_name": "AskUserQuestion"}, "enriching"))
        self.assertFalse(should_block({"tool_name": "Skill"}, "enriching"))


if __name__ == "__main__":
    unittest.main()
