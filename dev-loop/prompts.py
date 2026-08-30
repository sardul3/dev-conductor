#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

SKIP = "<!-- PROMPT_CONTRACT_V1 -->"


def spec_prompt(key: str, run: Path, repo: Path, issue_md: str) -> str:
    return (
        f"Load skill `story-spec`. Ticket `{key}`.\n"
        f"Repo: `{repo}`\n"
        f"Write files only under `{run}`: `spec.md` when the grill is done, "
        f"then `SPEC_APPROVED` (and `APPROVED`) after the user confirms the spec — not the ticket. Then `SESSION_DONE` (and `STAGE_DONE`).\n"
        f"Do not implement. Do not open a PR.\n\n"
        f"## Jira {key}\n\n{issue_md}\n"
    )


def test_writer_prompt(key: str, run: Path, repo: Path, spec: str, contracts: str) -> str:
    return (
        f"{SKIP}\n\n"
        f"Load skill `test-writer` and `implement-terse`.\n"
        f"Ticket `{key}`. Repo `{repo}`.\n"
        f"Write failing tests from the spec + contracts. Do not implement production code.\n"
        f"Do not Read `src/main` or other implementation sources.\n"
        f"When tests exist, write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n\n"
        f"## Spec\n\n{spec}\n\n## Public contracts\n\n{contracts}\n"
    )


def writer_prompt(key: str, run: Path, repo: Path, spec: str, verify_log: str = "") -> str:
    extra = f"\n## Last verify log\n\n{verify_log}\n" if verify_log else ""
    return (
        f"{SKIP}\n\n"
        f"Load skill `tdd` and `implement-terse`.\n"
        f"Ticket `{key}`. Repo `{repo}`.\n"
        f"Load `verify-before-done`. Implement until the new tests pass. Do not weaken tests unless they contradict the spec "
        f"or fail to compile from syntax/IO mistakes.\n"
        f"If verify failed, spawn `debugger` (systematic-debugging) for root cause before patching.\n"
        f"Do not git commit. When done, write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n\n"
        f"## Spec\n\n{spec}\n{extra}"
    )


def review_prompt(key: str, run: Path, repo: Path, spec: str) -> str:
    return (
        f"{SKIP}\n\n"
        f"Load skill `dev-loop-review` and spawn `code-reviewer` on `git diff` vs the default branch.\n"
        f"Ticket `{key}`. Repo `{repo}`.\n"
        f"Write `{run / 'verdict.json'}` with keys verdict, summary, risks "
        f"(verdict one of: excellent, good, good-with-risks, needs_improvement, blocker).\n"
        f"Then write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n"
        f"Do not implement unless you are not the reviewer.\n\n"
        f"## Spec\n\n{spec}\n"
    )


def simplify_prompt(key: str, run: Path, repo: Path, spec: str) -> str:
    return (
        f"{SKIP}\n\n"
        f"Load skill `tdd` if tests change; spawn `code-simplifier` on the git diff only.\n"
        f"Ticket `{key}`. Repo `{repo}`.\n"
        f"Simplify recently changed code. Do not change behavior or public contracts.\n"
        f"Do not git commit. When done, write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n\n"
        f"## Spec\n\n{spec}\n"
    )


def comment_fixer_prompt(key: str, run: Path, repo: Path, comments: str) -> str:
    return (
        f"{SKIP}\n\n"
        f"Load skill `pr-comment-fixer`. Ticket `{key}`. Repo `{repo}`.\n"
        f"Address the PR comments. Simple nits: implement (tdd). Needs design: decide then implement.\n"
        f"Do not use GitHub MCP; use `gh`. After changes: commit if the loop already shipped, "
        f"push, `gh pr comment` a short note, re-request review.\n"
        f"When done, write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n\n"
        f"## Comments\n\n{comments}\n"
    )
