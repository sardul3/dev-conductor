#!/usr/bin/env python3
"""Tests: merge UserPromptSubmit without wiping CCR env / apiKeyHelper."""

from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from merge_settings import merge_hook, merge_user_prompt_submit  # noqa: E402

CCR = {
    "apiKeyHelper": "/tmp/claude-code-router/bin/ccr-helper",
    "env": {
        "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456",
        "CCR_CLAUDE_CODE_MODEL": "OpenRouter/cohere/north-mini-code:free",
    },
    "permissions": {"allow": ["Bash"], "deny": []},
    "model": "sonnet",
}


class MergeSettingsTests(unittest.TestCase):
    def test_preserves_ccr_and_adds_hook(self) -> None:
        out = merge_user_prompt_submit(deepcopy(CCR), "/tmp/classify.py")
        self.assertEqual(CCR["env"], out["env"])
        self.assertEqual(CCR["apiKeyHelper"], out["apiKeyHelper"])
        self.assertEqual(CCR["permissions"], out["permissions"])
        blob = json.dumps(out["hooks"])
        self.assertIn("/tmp/classify.py", blob)
        self.assertIn("UserPromptSubmit", out["hooks"])

    def test_idempotent(self) -> None:
        once = merge_user_prompt_submit(deepcopy(CCR), "/tmp/classify.py")
        twice = merge_user_prompt_submit(once, "/tmp/classify.py")
        self.assertEqual(once["hooks"], twice["hooks"])

    def test_keeps_existing_other_hooks(self) -> None:
        src = deepcopy(CCR)
        src["hooks"] = {
            "PreToolUse": [
                {"hooks": [{"type": "command", "command": "echo pre"}]}
            ]
        }
        out = merge_user_prompt_submit(src, "/tmp/classify.py")
        self.assertIn("PreToolUse", out["hooks"])
        self.assertIn("UserPromptSubmit", out["hooks"])

    def test_session_start_preserves_ccr(self) -> None:
        out = merge_hook(deepcopy(CCR), "SessionStart", "bash /tmp/ensure_prompt_log_proxy.sh")
        self.assertEqual(CCR["env"], out["env"])
        self.assertEqual(CCR["apiKeyHelper"], out["apiKeyHelper"])
        self.assertIn("SessionStart", out["hooks"])
        self.assertIn("ensure_prompt_log_proxy.sh", json.dumps(out["hooks"]))

    def test_timeout_patched_on_existing_hook(self) -> None:
        once = merge_hook(deepcopy(CCR), "UserPromptSubmit", "/tmp/classify.py", timeout=15)
        twice = merge_hook(once, "UserPromptSubmit", "/tmp/classify.py", timeout=15)
        blob = json.dumps(twice["hooks"])
        self.assertEqual(1, blob.count("/tmp/classify.py"))
        self.assertIn('"timeout": 15', blob)


if __name__ == "__main__":
    unittest.main()
