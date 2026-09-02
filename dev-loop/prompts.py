#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

SKIP = "<!-- PROMPT_CONTRACT_V1 -->"


def spec_prompt(key: str, run: Path, repo: Path, issue_md: str, *, lavish: bool = False, arch: bool = False) -> str:
    extra = (
        "Load skill `lavish-ui`. This repo is UI (`lavish.enabled` resolved on). "
        "Keep Jira AC in `spec.md`. HTML is collaboration, not the contract.\n"
        if lavish else ""
    )
    arch_extra = (
        "Load skill `arch-studio` and `references/dev-loop.md`. `arch_studio.json` is enabled. "
        f"After `spec.md`, build the architecture pack under `{run / 'architecture'}`, open "
        f"`review.html` with Cursor `open_resource`, run the in-chat approve/reject gate "
        f"(`dev-loop arch approve {key}` / `dev-loop arch reject {key}`), then ask to approve the spec.\n"
        if arch else ""
    )
    return (
        f"Load skill `story-spec`. Ticket `{key}`.\n"
        f"Repo: `{repo}`\n"
        f"{extra}{arch_extra}"
        f"Grill with Cursor AskQuestion: recommended choice first (label ends with (Recommended)), "
        f"at most 4 options per question, whole frontier in one AskQuestion call. "
        f"Do not paste CLI --help or argparse usage into chat.\n"
        f"Write `spec.md` under `{run}` when the grill is done. "
        f"After the user confirms the spec (not the ticket), run `dev-loop approve {key}` — "
        f"do not write SPEC_APPROVED, APPROVED, STAGE_DONE, or SESSION_DONE yourself.\n"
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


def writer_prompt(key: str, run: Path, repo: Path, spec: str, verify_log: str = "", *, lavish: bool = False) -> str:
    extra = f"\n## Last verify log\n\n{verify_log}\n" if verify_log else ""
    ui = (
        "Load `lavish-ui` for visual slices. Keep markdown spec as the contract.\n"
        if lavish else ""
    )
    return (
        f"{SKIP}\n\n"
        f"Load skill `tdd` and `implement-terse`.\n"
        f"Ticket `{key}`. Repo `{repo}`.\n"
        f"{ui}"
        f"Load `verify-before-done`. Implement until the new tests pass. After tests are green, write terminal "
        f"snapshots (png/jpg/webp/gif/webm/mp4: tests.png, run.png, curl.png) to `{run / 'evidence'}` before STAGE_DONE. "
        f"Do not weaken tests unless they contradict the spec "
        f"or fail to compile from syntax/IO mistakes.\n"
        f"If verify failed, spawn `debugger` (systematic-debugging) for root cause before patching.\n"
        f"Docs: load `domain-glossary` only if a domain term or a hard-to-reverse decision changed. If self-review or user feedback corrected a durable convention, load `agent-memory` and update one relevant file. "
        f"Update README only if install, usage, or a public API would otherwise be wrong. Skip otherwise. Do not invent ADRs.\n"
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
        f"If a durable convention miss appears, add it to `verdict.json` as `metadata[]` (`target` agents|rule|context|readme, `text`, optional `path`/`globs`/`reason`). The conductor applies it when `agent_memory.auto_apply` is on; otherwise load `agent-memory` / `cli.py agent-memory`. Reviewer is read-only on those files.\nDo not implement unless you are not the reviewer.\n\n"
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
        f"Load skill `pr-comment-fixer`. If a comment corrects a durable agent convention, write `metadata[]` into the run `verdict.json` (or a small `memory.json`) and run `cli.py agent-memory --repo … --verdict …`, or load `agent-memory`. Ticket `{key}`. Repo `{repo}`.\n"
        f"Address the PR comments. Simple nits: implement (tdd). Needs design: decide then implement.\n"
        f"Do not use GitHub MCP; use `gh`. After changes: commit if the loop already shipped, "
        f"push, `gh pr comment` a short note, re-request review.\n"
        f"When done, write `{run / 'SESSION_DONE'}` and `{run / 'STAGE_DONE'}`.\n\n"
        f"## Comments\n\n{comments}\n"
    )
