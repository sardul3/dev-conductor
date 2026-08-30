#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from config import DevLoopConfig, jira_creds
from jira_client import jira_request, search_keys


def find_transition_id(data: dict[str, Any], name: str) -> str | None:
    want = (name or "").strip().lower()
    if not want:
        return None
    for t in data.get("transitions") or []:
        if str(t.get("name") or "").strip().lower() == want:
            return str(t.get("id") or "") or None
    return None


def comment_payload(text: str) -> dict[str, Any]:
    return {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    }


def transition_payload(tid: str) -> dict[str, Any]:
    return {"transition": {"id": str(tid)}}


def _issue_path(cfg: DevLoopConfig, key: str, suffix: str = "") -> str:
    base = cfg.jira.issue_path.format(key=key)
    return base.rstrip("/") + suffix


def progress(cfg: DevLoopConfig, key: str, event: str, comment: str = "", urlopen: Any = None) -> None:
    wf = cfg.workflow
    if not wf.enabled:
        return
    name = str(getattr(wf, event, "") or "")
    try:
        base, email, token = jira_creds(cfg)
    except SystemExit as exc:
        print(f"dev-loop: jira {event} skipped (creds): {exc}")
        return
    timeout = cfg.jira.timeout_sec
    if name:
        try:
            trans = jira_request(
                base,
                email,
                token,
                _issue_path(cfg, key, "/transitions"),
                timeout=timeout,
                urlopen=urlopen,
            )
            tid = find_transition_id(trans if isinstance(trans, dict) else {}, name)
            if not tid:
                print(f"dev-loop: jira transition {name!r} not found for {key}")
            else:
                jira_request(
                    base,
                    email,
                    token,
                    _issue_path(cfg, key, "/transitions"),
                    method="POST",
                    payload=transition_payload(tid),
                    timeout=timeout,
                    urlopen=urlopen,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: jira transition {event} failed: {exc}")
    if wf.comment_on_progress and comment:
        try:
            add_comment(cfg, key, comment, urlopen=urlopen)
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: jira comment failed: {exc}")
    if event == "on_merge":
        try:
            add_to_deploy_ticket(cfg, key, urlopen=urlopen)
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: deploy ticket update failed: {exc}")


def add_comment(cfg: DevLoopConfig, key: str, text: str, urlopen: Any = None) -> None:
    base, email, token = jira_creds(cfg)
    jira_request(
        base,
        email,
        token,
        _issue_path(cfg, key, "/comment"),
        method="POST",
        payload=comment_payload(text),
        timeout=cfg.jira.timeout_sec,
        urlopen=urlopen,
    )


def add_to_deploy_ticket(cfg: DevLoopConfig, closed_key: str, urlopen: Any = None) -> None:
    wf = cfg.workflow
    dest = (wf.deploy_ticket_key or "").strip()
    if not dest and wf.deploy_ticket_jql:
        base, email, token = jira_creds(cfg)
        keys = search_keys(
            base,
            email,
            token,
            wf.deploy_ticket_jql,
            max_results=1,
            search_path=cfg.jira.search_path,
            timeout=cfg.jira.timeout_sec,
            urlopen=urlopen,
        )
        dest = keys[0] if keys else ""
    if not dest:
        return
    add_comment(cfg, dest, f"Ready for deploy: {closed_key}", urlopen=urlopen)
