#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

UrlOpen = Callable[..., Any]


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
