from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mini_yaml import loads


class MiniYamlTests(unittest.TestCase):
    def test_given_nested_mapping_when_loads_then_jql_and_empty_list(self) -> None:
        data = loads(
            """
# c
jira:
  project: ASE
  jql: 'assignee = currentUser()'
denylist: []
health: {}
cache_minutes: 10
"""
        )
        self.assertEqual(data["jira"]["project"], "ASE")
        self.assertEqual(data["jira"]["jql"], "assignee = currentUser()")
        self.assertEqual(data["denylist"], [])
        self.assertEqual(data["cache_minutes"], 10)
        self.assertEqual(data["health"], {})
