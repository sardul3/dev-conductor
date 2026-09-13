#!/usr/bin/env python3
"""RED tests for model router. Run: python3 -m unittest tests.test_route_model"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from route_model import detect_backend, infer_profile, resolve  # noqa: E402


class DetectBackendTests(unittest.TestCase):
    def test_explicit_ccr(self) -> None:
        self.assertEqual("ccr", detect_backend({"PROMPT_ENRICH_BACKEND": "ccr"}, {}))

    def test_explicit_anthropic(self) -> None:
        self.assertEqual(
            "anthropic",
            detect_backend({"PROMPT_ENRICH_BACKEND": "anthropic", "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"}, {}),
        )

    def test_localhost_gateway_defaults_anthropic(self) -> None:
        self.assertEqual("anthropic", detect_backend({"ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"}, {}))

    def test_localhost_gateway_explicit_ccr(self) -> None:
        self.assertEqual(
            "ccr",
            detect_backend({"PROMPT_ENRICH_BACKEND": "ccr", "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"}, {}),
        )

    def test_plain_anthropic(self) -> None:
        self.assertEqual("anthropic", detect_backend({}, {}))


class ResolveTests(unittest.TestCase):
    def test_ccr_code_profile(self) -> None:
        from route_model import load_catalog

        catalog = load_catalog(ROOT / "model-router.ccr.yaml", backend="ccr")
        r = resolve("code", backend="ccr", catalog=catalog)
        self.assertEqual("OpenRouter/poolside/laguna-s-2.1:free", r.primary)
        self.assertEqual("OpenRouter/nvidia/nemotron-3-super-120b-a12b:free", r.fallback)

    def test_anthropic_code_profile(self) -> None:
        r = resolve("code", backend="anthropic")
        self.assertEqual("sonnet", r.primary)
        self.assertEqual("opus", r.fallback)

    def test_each_profile_both_catalogs(self) -> None:
        expected = {
            ("ccr", "fast"): "OpenRouter/poolside/laguna-xs-2.1:free",
            ("ccr", "code"): "OpenRouter/poolside/laguna-s-2.1:free",
            ("ccr", "reason"): "OpenRouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            ("ccr", "heavy"): "OpenRouter/nvidia/nemotron-3-ultra-550b-a55b:free",
            ("ccr", "vision"): "OpenRouter/nvidia/nemotron-nano-12b-v2-vl:free",
            ("anthropic", "fast"): "haiku",
            ("anthropic", "code"): "sonnet",
            ("anthropic", "reason"): "opus",
            ("anthropic", "heavy"): "opus",
            ("anthropic", "vision"): "sonnet",
        }
        from route_model import load_catalog

        ccr_catalog = load_catalog(ROOT / "model-router.ccr.yaml", backend="ccr")
        for (backend, profile), primary in expected.items():
            with self.subTest(backend=backend, profile=profile):
                catalog = ccr_catalog if backend == "ccr" else None
                r = resolve(profile, backend=backend, catalog=catalog)
                self.assertEqual(primary, r.primary)

    def test_unknown_profile_falls_to_code(self) -> None:
        r = resolve("nope", backend="anthropic")
        self.assertEqual("sonnet", r.primary)

    def test_override_profile_name(self) -> None:
        r = resolve("code", backend="anthropic", override="heavy")
        self.assertEqual("opus", r.primary)

    def test_override_alias_opus_on_ccr(self) -> None:
        from route_model import load_catalog

        catalog = load_catalog(ROOT / "model-router.ccr.yaml", backend="ccr")
        r = resolve("code", backend="ccr", override="opus", catalog=catalog)
        self.assertTrue(r.primary.startswith("OpenRouter/"))
        self.assertIn("ultra", r.primary.lower())
        self.assertTrue(r.primary.endswith(":free"))

    def test_ccr_catalog_is_free_only(self) -> None:
        from route_model import load_catalog

        from route_model import load_catalog

        data = load_catalog(ROOT / "model-router.ccr.yaml", backend="ccr")
        r = resolve("code", backend="ccr", catalog=data)
        self.assertGreaterEqual(len(r.fallbacks), 3)
        self.assertTrue(all(x.endswith(":free") or x.endswith("/free") for x in [r.primary, r.fallback, *r.fallbacks]))
        for profile, row in (data.get("ccr") or {}).items():
            for key in ("primary", "fallback"):
                val = str(row.get(key) or "")
                self.assertTrue(val.endswith(":free") or val.endswith("/free"), f"{profile}.{key}={val}")
            for val in row.get("fallbacks") or []:
                self.assertTrue(str(val).endswith(":free") or str(val).endswith("/free"), val)
        for alias, mapping in (data.get("aliases") or {}).items():
            ccr = str((mapping or {}).get("ccr") or "")
            self.assertTrue(ccr.endswith(":free") or ccr.endswith("/free"), f"alias {alias}={ccr}")

    def test_ccr_rejects_paid_openrouter_id(self) -> None:
        from route_model import assert_ccr_free

        with self.assertRaises(ValueError):
            assert_ccr_free("OpenRouter/anthropic/claude-sonnet-4.6")


class InferProfileTests(unittest.TestCase):
    def test_vision_beats_code(self) -> None:
        self.assertEqual("vision", infer_profile("implement the button", "screenshot of the UI", "code+tests"))

    def test_heavy_production(self) -> None:
        self.assertEqual("heavy", infer_profile("ship production auth across many files", "security review", "code"))

    def test_reason_debug(self) -> None:
        self.assertEqual("reason", infer_profile("investigate the deadlock", "logs", "analysis"))

    def test_code_implement(self) -> None:
        self.assertEqual("code", infer_profile("add unit tests for checkout", "repo", "code+tests"))

    def test_fast_plan_only(self) -> None:
        self.assertEqual("fast", infer_profile("outline options", "none", "plan only"))


if __name__ == "__main__":
    unittest.main()
