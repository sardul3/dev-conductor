from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from quality import gate_result, parse_pit_killed_pct, parse_snyk_ok

class QualityTests(unittest.TestCase):
    def test_given_pit_report_when_parse_then_killed_pct(self) -> None:
        text = ">> Generated 200 mutations Killed 150 (75%)"
        self.assertEqual(parse_pit_killed_pct(text), 75.0)

    def test_given_snyk_ok_json_when_parse_then_true(self) -> None:
        self.assertTrue(parse_snyk_ok('{"ok": true, "vulnerabilities": []}'))

    def test_given_snyk_high_when_fail_on_high_then_false(self) -> None:
        raw = '{"ok": false, "vulnerabilities": [{"severity": "high"}]}'
        self.assertFalse(parse_snyk_ok(raw, fail_on="high"))

    def test_given_low_only_when_fail_on_high_then_true(self) -> None:
        raw = '{"ok": false, "vulnerabilities": [{"severity": "low"}]}'
        self.assertTrue(parse_snyk_ok(raw, fail_on="high"))

    def test_given_killed_70_when_min_75_then_fail(self) -> None:
        ok, _ = gate_result("mutation", 70.0, 75.0, metric="killed")
        self.assertFalse(ok)

    def test_given_killed_80_when_min_75_then_pass(self) -> None:
        ok, _ = gate_result("mutation", 80.0, 75.0, metric="killed")
        self.assertTrue(ok)

    def test_given_survived_metric_when_above_ceiling_then_fail(self) -> None:
        ok, _ = gate_result("mutation", 40.0, 25.0, metric="survived")
        self.assertFalse(ok)

    def test_given_survived_metric_when_under_ceiling_then_pass(self) -> None:
        ok, _ = gate_result("mutation", 10.0, 25.0, metric="survived")
        self.assertTrue(ok)
