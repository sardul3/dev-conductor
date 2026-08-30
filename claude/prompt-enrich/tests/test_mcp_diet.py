#!/usr/bin/env python3
"""RED tests: strip Jira/IdentityIQ from user-scoped MCP."""

from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_diet import HEAVY_SERVERS, strip_user_servers  # noqa: E402


class McpDietTests(unittest.TestCase):
    def test_removes_jira_and_identityiq_keeps_others(self) -> None:
        src = {
            "mcpServers": {
                "jira": {"type": "sse", "url": "https://mcp.atlassian.com/v1/sse"},
                "identityiq": {"type": "http", "url": "http://127.0.0.1:8766/mcp"},
                "keep-me": {"type": "stdio", "command": "echo"},
            }
        }
        out, extracted = strip_user_servers(deepcopy(src))
        self.assertEqual(["keep-me"], sorted(out["mcpServers"].keys()))
        self.assertEqual(set(HEAVY_SERVERS), set(extracted.keys()))
        self.assertEqual(src["mcpServers"]["jira"], extracted["jira"])

    def test_idempotent_when_already_gone(self) -> None:
        src = {"mcpServers": {"keep-me": {"command": "x"}}}
        out, extracted = strip_user_servers(deepcopy(src))
        self.assertEqual(src, out)
        self.assertEqual({}, extracted)


if __name__ == "__main__":
    unittest.main()
