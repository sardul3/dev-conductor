#!/usr/bin/env python3
"""RED tests: hard skips stay deterministic; new-task vs skip is a stubbed LLM."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from classify import classify, extract_prompt, parse_yn  # noqa: E402


class ClassifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, prompt: str, session: str = "s1", env: dict | None = None, phase: str | None = None, llm=None) -> str:
        if phase:
            p = self.state_dir / f"{session}.json"
            p.write_text(json.dumps({"phase": phase}), encoding="utf-8")
        return classify(prompt, session, self.state_dir, env or {}, llm=llm)

    def test_skip_marker(self) -> None:
        self.assertEqual("skip", self._run("<!-- PROMPT_CONTRACT_V1 -->\n# Task\nimplement auth", llm=lambda _: "Y"))

    def test_skip_enrich_prefix(self) -> None:
        self.assertEqual("skip", self._run("/skip-enrich implement a payment service", llm=lambda _: "Y"))

    def test_skip_enrich_clears_handed_off_so_this_tab_can_work(self) -> None:
        import json as _json
        self._run("x", phase="handed_off", llm=lambda _: "N")
        self.assertEqual(
            "skip",
            self._run("/skip-enrich do it here", session="s1", llm=lambda _: "Y"),
        )
        phase = _json.loads((self.state_dir / "s1.json").read_text(encoding="utf-8"))["phase"]
        self.assertEqual("done", phase)

    def test_skip_other_slash_commands(self) -> None:
        self.assertEqual("skip", self._run("/compact", llm=lambda _: "Y"))

    def test_deep_ask_forces_inject(self) -> None:
        self.assertEqual("inject", self._run("/deep-ask look at this", llm=lambda _: "N"))

    def test_skip_short_yes(self) -> None:
        self.assertEqual("skip", self._run("yes", llm=lambda _: "Y"))
        self.assertEqual("skip", self._run("do it", llm=lambda _: "Y"))

    def test_skip_resume_even_if_llm_says_yes(self) -> None:
        self.assertEqual("skip", self._run("resume", llm=lambda _: "Y"))
        self.assertEqual("skip", self._run("Resume", llm=lambda _: "Y"))
        self.assertEqual("skip", self._run("continue", llm=lambda _: "Y"))
        self.assertEqual("skip", self._run("proceed", llm=lambda _: "Y"))
        self.assertEqual("skip", self._run("/resume", llm=lambda _: "Y"))

    def test_llm_yes_injects_without_verb_list(self) -> None:
        self.assertEqual("inject", self._run("make this app prod ready", llm=lambda _: "Y"))
        self.assertEqual("inject", self._run("implement auth", llm=lambda _: "Y"))

    def test_llm_no_skips_log_glance(self) -> None:
        self.assertEqual("skip", self._run("look at this log from last night", llm=lambda _: "N"))

    def test_llm_error_fail_open(self) -> None:
        def boom(_prompt: str) -> str:
            raise TimeoutError("classifier down")

        self.assertEqual("skip", self._run("make this app prod ready", llm=boom))

    def test_skip_during_grilling_phase(self) -> None:
        self.assertEqual(
            "skip",
            self._run("implement a huge new billing engine", phase="grilling", llm=lambda _: "Y"),
        )

    def test_inject_after_done_phase(self) -> None:
        self.assertEqual("inject", self._run("implement auth", phase="done", llm=lambda _: "Y"))

    def test_skip_when_disabled(self) -> None:
        self.assertEqual("skip", self._run("implement auth", env={"PROMPT_ENRICH_DISABLE": "1"}, llm=lambda _: "Y"))

    def test_fail_open_empty_prompt(self) -> None:
        self.assertEqual("skip", self._run("   ", llm=lambda _: "Y"))

    def test_parse_yn(self) -> None:
        self.assertEqual("Y", parse_yn("Y"))
        self.assertEqual("N", parse_yn("n\n"))
        self.assertEqual("Y", parse_yn("Answer: Y"))
        self.assertIsNone(parse_yn(""))

    def test_extract_prompt_fallback_keys(self) -> None:
        self.assertEqual("hello", extract_prompt({"user_prompt": "hello"}))
        self.assertEqual("hello", extract_prompt({"prompt": "hello"}))
        self.assertEqual("", extract_prompt({}))


if __name__ == "__main__":
    unittest.main()
