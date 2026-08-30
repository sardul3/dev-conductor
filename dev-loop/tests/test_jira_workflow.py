from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jira_client import jira_request
from jira_workflow import comment_payload, find_transition_id, transition_payload


class FakeResp:
    def __init__(self, payload: dict | None, status: int = 200) -> None:
        self._payload = json.dumps(payload).encode() if payload is not None else b""
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class JiraWorkflowTests(unittest.TestCase):
    def test_given_transitions_when_find_by_name_then_id(self) -> None:
        data = {
            "transitions": [
                {"id": "11", "name": "In Progress"},
                {"id": "21", "name": "In Review"},
            ]
        }
        self.assertEqual(find_transition_id(data, "in review"), "21")
        self.assertIsNone(find_transition_id(data, "Done"))

    def test_given_text_when_comment_payload_then_adf_doc(self) -> None:
        body = comment_payload("shipped ASE-1")
        self.assertEqual(body["body"]["type"], "doc")
        text = body["body"]["content"][0]["content"][0]["text"]
        self.assertEqual(text, "shipped ASE-1")

    def test_given_id_when_transition_payload_then_nested_id(self) -> None:
        self.assertEqual(transition_payload("21"), {"transition": {"id": "21"}})

    def test_given_post_when_jira_request_then_sends_json_body(self) -> None:
        captured: list[Request] = []

        def urlopen(req: Request, timeout: int = 0) -> FakeResp:
            captured.append(req)
            return FakeResp({"ok": True})

        jira_request(
            "https://ex.atlassian.net",
            "a@b.com",
            "tok",
            "/rest/api/3/issue/ASE-1/comment",
            method="POST",
            payload={"body": {"type": "doc"}},
            urlopen=urlopen,
        )
        req = captured[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn(b'"type": "doc"', req.data or b"")
        ctype = req.headers.get("Content-type") or req.headers.get("Content-Type") or ""
        self.assertIn("application/json", ctype)
