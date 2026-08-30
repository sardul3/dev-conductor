#!/usr/bin/env python3
"""Tests for launch file prep (skip marker, dual-backend env, copies)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from launch_prep import prepare_launch  # noqa: E402


CONTRACT = """# Task
Build auth.

## Goal
implement login

## Context
this repo

## Output format
code+tests

## Model
- profile: code
"""


class LaunchPrepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.project = Path(self.tmp.name) / "project"
        self.home.mkdir()
        self.project.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_writes_skip_marker_and_runs_path(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-1",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="anthropic",
            env={},
            now_utc="2026-08-29T16:00:00Z",
        )
        prompt = Path(result["prompt_file"])
        self.assertTrue(prompt.is_file())
        text = prompt.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("<!-- PROMPT_CONTRACT_V1 -->"))
        self.assertIn("backend: anthropic", text)
        self.assertIn("model: sonnet", text)
        self.assertIn("fallback: opus", text)
        copy = self.project / "prompts" / "enriched-2026-08-29T16-00-00Z.md"
        self.assertTrue(copy.is_file())

    def test_anthropic_runner_unsets_ccr_env(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-1",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="anthropic",
            env={},
        )
        runner = Path(result["runner_file"]).read_text(encoding="utf-8")
        self.assertIn("unset ANTHROPIC_BASE_URL", runner)
        self.assertIn("claude --model", runner)
        self.assertIn("--fallback-model", runner)

    def test_ccr_runner_inherits_env(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-1",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="ccr",
            env={"ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"},
        )
        runner = Path(result["runner_file"]).read_text(encoding="utf-8")
        self.assertNotIn("unset ANTHROPIC_BASE_URL", runner)
        self.assertIn("OpenRouter/poolside/laguna-s-2.1:free", runner)

    def test_state_phase_handed_off(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-9",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="anthropic",
            env={},
        )
        state = json.loads((self.home / ".claude" / "prompt-enrichment" / "state" / "sess-9.json").read_text())
        self.assertEqual("handed_off", state["phase"])
        self.assertEqual("sonnet", state["model_id"])
        self.assertEqual(result["primary"], "sonnet")

    def test_work_session_contract_and_env(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-work",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="ccr",
            env={},
        )
        text = Path(result["prompt_file"]).read_text(encoding="utf-8")
        self.assertIn("## Work session", text)
        self.assertIn("no filler", text.lower())
        self.assertIn("re-read", text.lower())
        runner = Path(result["runner_file"]).read_text(encoding="utf-8")
        self.assertIn("PROMPT_ENRICH_WORK_SESSION=1", runner)

    def test_given_budget_env_when_prepare_then_runner_has_max_budget_usd(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-budget",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="anthropic",
            env={"DEVLOOP_MAX_BUDGET_USD": "2.5"},
        )
        runner = Path(result["runner_file"]).read_text(encoding="utf-8")
        self.assertIn("--max-budget-usd 2.5", runner)

    def test_given_zero_budget_env_when_prepare_then_runner_omits_flag(self) -> None:
        result = prepare_launch(
            CONTRACT,
            session_id="sess-budget-zero",
            cwd=str(self.project),
            home=self.home,
            project_dir=self.project,
            backend="anthropic",
            env={"DEVLOOP_MAX_BUDGET_USD": "0"},
        )
        runner = Path(result["runner_file"]).read_text(encoding="utf-8")
        self.assertNotIn("--max-budget-usd", runner)


if __name__ == "__main__":
    unittest.main()
