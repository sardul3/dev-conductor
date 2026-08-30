from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from config import DevLoopConfig
from poller import decide, poll_once, poller_plist

class PollerTests(unittest.TestCase):
    def test_given_merged_when_decide_then_done(self) -> None:
        self.assertEqual(decide({"state": "MERGED"}, auto_merge=False), "done")

    def test_given_changes_requested_when_decide_then_fix(self) -> None:
        pr = {"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED", "statusCheckRollup": []}
        self.assertEqual(decide(pr, auto_merge=False), "fix")

    def test_given_failing_checks_when_decide_then_fix(self) -> None:
        pr = {
            "state": "OPEN",
            "reviewDecision": None,
            "statusCheckRollup": [{"state": "FAILURE", "name": "ci"}],
        }
        self.assertEqual(decide(pr, auto_merge=False), "fix")

    def test_given_approved_green_when_auto_merge_then_merge(self) -> None:
        pr = {
            "state": "OPEN",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"state": "SUCCESS"}],
        }
        self.assertEqual(decide(pr, auto_merge=True), "merge")

    def test_given_approved_green_when_not_auto_then_alert(self) -> None:
        pr = {
            "state": "OPEN",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"state": "SUCCESS"}],
        }
        self.assertEqual(decide(pr, auto_merge=False), "alert")

    def test_given_new_review_comment_when_decide_then_fix(self) -> None:
        pr = {
            "state": "OPEN",
            "reviewDecision": None,
            "statusCheckRollup": [{"state": "SUCCESS"}],
            "comments": [{"author": {"login": "alice"}, "body": "please rename"}],
        }
        self.assertEqual(decide(pr, auto_merge=False, bot_logins={"devloop-bot"}), "fix")

    def test_given_approved_when_poll_once_auto_merge_then_merge(self) -> None:
        cfg = DevLoopConfig()
        cfg.poller.auto_merge = True
        cfg.poller.notify = False
        merged: list[int] = []
        def view(_item):
            return {"state": "OPEN", "reviewDecision": "APPROVED", "statusCheckRollup": [{"state": "SUCCESS"}]}
        def merge(item):
            merged.append(int(item["pr"]))
        actions = poll_once(
            cfg,
            watches=[{"pr": 4, "repo": "/r", "key": "A-1", "branch": "b"}],
            view_pr=view,
            merge_pr=merge,
            launch_fix=lambda *_: None,
            alert=lambda *_: None,
            on_done=lambda *_: None,
        )
        self.assertEqual(actions, ["done"])
        self.assertEqual(merged, [4])

    def test_given_same_fingerprint_when_poll_then_skip_fix(self) -> None:
        from poller import comment_fingerprint
        cfg = DevLoopConfig()
        pr = {
            "state": "OPEN",
            "reviewDecision": "CHANGES_REQUESTED",
            "statusCheckRollup": [],
            "comments": [{"author": {"login": "alice"}, "body": "rename"}],
        }
        fp = comment_fingerprint(pr)
        launched: list[int] = []
        actions = poll_once(
            cfg,
            watches=[{"pr": 8, "repo": "/r", "key": "A-1", "branch": "b", "last_fp": fp}],
            view_pr=lambda _i: pr,
            merge_pr=lambda _i: None,
            launch_fix=lambda item, _pr: launched.append(item["pr"]),
            alert=lambda _i: None,
            on_done=lambda _i: None,
        )
        self.assertEqual(actions, ["wait"])
        self.assertEqual(launched, [])

    def test_given_interval_when_plist_then_seconds(self) -> None:
        xml = poller_plist("com.x", "/usr/bin/python3", "/tmp/cli.py", 1800, "/tmp/p.log")
        self.assertIn("<integer>1800</integer>", xml)
        self.assertIn("<string>poll</string>", xml)
