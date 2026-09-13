from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prompts import spec_prompt  # noqa: E402


class PromptTests(unittest.TestCase):
    def test_given_spec_prompt_when_built_then_requires_ask_question(self) -> None:
        text = spec_prompt("LCN-2", Path("/runs/LCN-2"), Path("/dev/repo"), "Initialize Python project")
        self.assertIn("AskQuestion", text)
        self.assertIn("(Recommended)", text)
        self.assertIn("Do not paste CLI --help", text)
        self.assertIn("story-spec", text)
        self.assertIn("approve LCN-2", text)
        self.assertIn("do not write SPEC_APPROVED", text)
