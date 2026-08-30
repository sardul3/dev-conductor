from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jira_client import adf_to_text, get_issue, search_keys


class FakeResp:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class JiraClientTests(unittest.TestCase):
    def test_given_adf_when_adf_to_text_then_joins_text_nodes(self) -> None:
        node = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "World"}]},
            ],
        }
        self.assertEqual(adf_to_text(node), "Hello\nWorld")

    def test_given_search_json_when_search_keys_then_returns_keys_only(self) -> None:
        captured: list[Request] = []

        def urlopen(req: Request, timeout: int = 0) -> FakeResp:
            captured.append(req)
            return FakeResp({"issues": [{"key": "ASE-1"}, {"key": "ASE-2"}]})

        keys = search_keys("https://ex.atlassian.net", "a@b.com", "tok", "project = ASE", urlopen=urlopen)
        self.assertEqual(keys, ["ASE-1", "ASE-2"])
        self.assertIn("/rest/api/3/search/jql", captured[0].full_url)
        self.assertTrue(captured[0].get_header("Authorization") or captured[0].headers.get("Authorization"))

    def test_given_issue_json_when_get_issue_then_flattens_fields(self) -> None:
        def urlopen(req: Request, timeout: int = 0) -> FakeResp:
            return FakeResp(
                {
                    "key": "ASE-9",
                    "fields": {
                        "summary": "Add health",
                        "description": {"type": "doc", "content": [{"type": "text", "text": "Do it"}]},
                        "status": {"name": "To Do"},
                        "issuetype": {"name": "Story"},
                        "labels": ["be"],
                        "comment": {
                            "comments": [
                                {
                                    "author": {"displayName": "Sam"},
                                    "body": {"type": "doc", "content": [{"type": "text", "text": "ack"}]},
                                }
                            ]
                        },
                    },
                }
            )

        issue = get_issue("https://ex.atlassian.net", "a@b.com", "t", "ASE-9", urlopen=urlopen)
        self.assertEqual(issue["key"], "ASE-9")
        self.assertEqual(issue["summary"], "Add health")
        self.assertEqual(issue["description"], "Do it")
        self.assertEqual(issue["status"], "To Do")
        self.assertEqual(issue["issuetype"], "Story")
        self.assertEqual(issue["comments"], ["Sam: ack"])
