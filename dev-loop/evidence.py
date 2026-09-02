#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

UrlOpen = Callable[..., Any]

VISUAL_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".webm", ".mp4"}


class VisualEvidenceMissing(RuntimeError):
    """Ship gate: require_visual is on and runs/KEY/evidence/ has no image/video."""


def evidence_dir(run: Path) -> Path:
    return Path(run) / "evidence"


def list_visual_evidence(run: Path | None) -> list[Path]:
    if run is None:
        return []
    dest = evidence_dir(run)
    if not dest.is_dir():
        return []
    files: list[Path] = []
    for p in sorted(dest.iterdir()):
        if p.is_file() and p.suffix.lower() in VISUAL_SUFFIXES:
            files.append(p)
    return files


def require_visual_evidence(cfg: Any, run: Path | None) -> list[Path]:
    ev = getattr(cfg, "evidence", None)
    required = True if ev is None else bool(getattr(ev, "require_visual", True))
    files = list_visual_evidence(run)
    if not required:
        return files
    if files:
        return files
    dest = evidence_dir(run) if run is not None else Path("runs/KEY/evidence")
    raise VisualEvidenceMissing(
        "dev-loop: visual evidence required. Write snapshots "
        f"(png/jpg/webp/gif/webm/mp4: tests.png, run.png, curl.png) to {dest} "
        "then step again. Do not open a PR without them. Text-only verify.log is not enough."
    )


def visual_markdown(files: list[Path] | list[str]) -> str:
    lines: list[str] = []
    for item in files:
        p = Path(item)
        if not p.name:
            continue
        lines.append(f"![{p.stem}]({p.name})")
    return "\n".join(lines)


def comment_visual_evidence(
    repo: Path,
    pr_number: int,
    files: list[Path],
    gh_bin: str = "gh",
) -> bool:
    """Attach run-dir snapshots via `gh pr comment --attach`. Does not commit pngs."""
    if not files or not pr_number:
        return False
    body_lines = ["## Evidence", ""]
    for p in files:
        body_lines.append(f"![{p.stem}]({p})")
    body = "\n".join(body_lines) + "\n"
    cmd = [gh_bin, "pr", "comment", str(pr_number), "--body", body]
    for p in files:
        cmd.extend(["--attach", str(p)])
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    if proc.returncode == 0:
        return True
    fallback = [gh_bin, "pr", "comment", str(pr_number), "--body", body]
    proc2 = subprocess.run(fallback, cwd=str(repo), capture_output=True, text=True)
    err = (proc.stderr or proc.stdout or proc2.stderr or proc2.stdout or "").strip()
    if proc2.returncode == 0:
        print("dev-loop: gh pr comment posted without --attach (upgrade gh to upload snapshots)")
        return True
    print(f"dev-loop: evidence comment failed: {err}")
    return False


def render_http_markdown(
    method: str,
    url: str,
    status: int | None,
    body: str,
    error: str | None = None,
) -> str:
    lines = [f"### {method} {url}", ""]
    if error:
        lines.append(f"error: {error}")
    if status is not None:
        lines.append(f"status: {status}")
    lines.append("")
    lines.append("```")
    lines.append((body or "")[:4000])
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def capture_http(
    probes: list[dict[str, Any]],
    urlopen: UrlOpen | None = None,
    timeout: int = 8,
) -> str:
    opener = urlopen or urllib.request.urlopen
    chunks: list[str] = ["# Evidence (HTTP probes)", ""]
    for probe in probes:
        method = str(probe.get("method") or "GET").upper()
        url = str(probe.get("url") or "")
        if not url:
            continue
        data = probe.get("body")
        raw = data.encode() if isinstance(data, str) and data else None
        req = urllib.request.Request(url, data=raw, method=method)
        try:
            with opener(req, timeout=timeout) as resp:
                status = int(getattr(resp, "status", 200) or 200)
                body = resp.read().decode("utf-8", errors="replace")
            chunks.append(render_http_markdown(method, url, status, body))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:4000]
            chunks.append(render_http_markdown(method, url, int(exc.code), body, error=str(exc)))
        except Exception as exc:  # noqa: BLE001
            chunks.append(render_http_markdown(method, url, None, "", error=str(exc)))
    return "\n".join(chunks).rstrip() + "\n"


def capture_playwright(repo: Path, cmd: str, timeout: int = 180) -> str:
    parts = cmd.split()
    proc = subprocess.run(parts, cwd=str(repo), capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return f"# Evidence (playwright)\n\nexit {proc.returncode}\n\n```\n{out[:8000]}\n```\n"


def capture_evidence(cfg: Any, repo: Path, dest: Path) -> str:
    ev = getattr(cfg, "evidence", None)
    if ev is None or not ev.enabled:
        return ""
    timeout = int(ev.timeout_sec or 8)
    if ev.mode == "playwright" and ev.playwright_cmd:
        md = capture_playwright(repo, ev.playwright_cmd, timeout=max(timeout, 60))
    else:
        md = capture_http(list(ev.probes or []), timeout=timeout)
    dest.write_text(md, encoding="utf-8")
    return md
