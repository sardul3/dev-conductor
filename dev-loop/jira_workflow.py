#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

from config import DEFAULT_ON_PR_COMMENT, DevLoopConfig, jira_creds
from gitutil import github_pr_url, github_remote
from jira_client import adf_to_text, jira_request, search_keys

ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def format_on_pr_comment(
    template: str = "",
    *,
    number: int | None = None,
    branch: str = "",
    url: str = "",
    remote: str | None = None,
) -> str:
    resolved = (url or "").strip() or github_pr_url(remote, number)
    n = "" if number is None else str(int(number))
    values = {
        "number": n,
        "pr": n,
        "pr_number": n,
        "branch": branch or "",
        "pr_url": resolved,
        "url": resolved,
    }
    tmpl = (template or "").strip() or DEFAULT_ON_PR_COMMENT
    try:
        text = tmpl.format(**values)
    except (KeyError, ValueError, IndexError):
        text = DEFAULT_ON_PR_COMMENT.format(**values)
    text = text.strip()
    if resolved and "https://" not in text:
        text = f"{text}\n{resolved}".strip()
    return text


def pr_comment_text(
    cfg: DevLoopConfig,
    number: int | None,
    branch: str,
    repo: Any = None,
    url: str = "",
) -> str:
    remote = github_remote(repo) if repo is not None else None
    return format_on_pr_comment(
        getattr(cfg.workflow, "on_pr_comment", "") or "",
        number=number,
        branch=branch,
        url=url,
        remote=remote,
    )


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


def assign_payload(account_id: str) -> dict[str, Any]:
    return {"accountId": str(account_id)}


def _issue_path(cfg: DevLoopConfig, key: str, suffix: str = "") -> str:
    base = cfg.jira.issue_path.format(key=key)
    return base.rstrip("/") + suffix


def _comment_texts(issue: dict[str, Any]) -> list[str]:
    block = (issue.get("fields") or {}).get("comment") or {}
    texts: list[str] = []
    for c in block.get("comments") or []:
        body = adf_to_text(c.get("body"))
        if body:
            texts.append(body)
    return texts


def _has_started_comment(issue: dict[str, Any], comment: str) -> bool:
    want = (comment or "").strip()
    marker = "dev-loop started"
    for text in _comment_texts(issue):
        if want and want in text:
            return True
        if marker in text.lower():
            return True
    return False


def _assignee_info(issue: dict[str, Any]) -> tuple[str, str]:
    raw = (issue.get("fields") or {}).get("assignee") or {}
    if not isinstance(raw, dict):
        return "", ""
    return str(raw.get("accountId") or ""), str(raw.get("displayName") or raw.get("emailAddress") or "")


def maybe_assign(
    cfg: DevLoopConfig,
    key: str,
    urlopen: Any = None,
    *,
    issue: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Assign the authenticated user when unassigned. Skip if another human owns it."""
    wf = cfg.workflow
    if not wf.assign_on_start and not wf.assign_force:
        return {"status": "skipped", "note": "assign_on_start is false"}
    try:
        base, email, token = jira_creds(cfg)
    except SystemExit as exc:
        print(f"dev-loop: jira assign skipped (creds): {exc}")
        return {"status": "skipped", "note": f"creds: {exc}"}
    timeout = cfg.jira.timeout_sec
    try:
        me = jira_request(
            base,
            email,
            token,
            "/rest/api/3/myself",
            timeout=timeout,
            urlopen=urlopen,
        )
        account_id = str((me or {}).get("accountId") or "")
        if not account_id:
            print("dev-loop: jira assign skipped (myself has no accountId)")
            return {"status": "skipped", "note": "myself has no accountId"}
        snap = issue
        if snap is None:
            snap = jira_request(
                base,
                email,
                token,
                _issue_path(cfg, key),
                query={"fields": "assignee,comment"},
                timeout=timeout,
                urlopen=urlopen,
            )
        if not isinstance(snap, dict):
            snap = {}
        other_id, other_name = _assignee_info(snap)
        if other_id and other_id == account_id:
            return {"status": "ok", "note": "already self"}
        if other_id and other_id != account_id and not wf.assign_force:
            label = other_name or other_id
            print(f"dev-loop: jira assign skipped (already {label})")
            return {"status": "skipped", "note": f"already {label}"}
        jira_request(
            base,
            email,
            token,
            _issue_path(cfg, key, "/assignee"),
            method="PUT",
            payload=assign_payload(account_id),
            timeout=timeout,
            urlopen=urlopen,
        )
        return {"status": "ok", "note": "assigned"}
    except Exception as exc:  # noqa: BLE001
        print(f"dev-loop: jira assign failed: {exc}")
        return {"status": "failed", "note": f"assign failed: {exc}"}


def progress(cfg: DevLoopConfig, key: str, event: str, comment: str = "", urlopen: Any = None) -> dict[str, str]:
    wf = cfg.workflow
    if not wf.enabled:
        print(f"dev-loop: jira {event} skipped (workflow.enabled is false)")
        return {"event": event, "status": "skipped", "note": "workflow.enabled is false"}
    ticket = (key or "").strip().upper()
    if not ISSUE_KEY.match(ticket):
        print(f"dev-loop: jira {event} skipped (bad key {key!r})")
        return {"event": event, "status": "skipped", "note": f"bad key {key!r}"}
    name = str(getattr(wf, event, "") or "")
    try:
        base, email, token = jira_creds(cfg)
    except SystemExit as exc:
        print(f"dev-loop: jira {event} skipped (creds): {exc}")
        return {"event": event, "status": "skipped", "note": f"creds: {exc}"}
    timeout = cfg.jira.timeout_sec
    notes: list[str] = []
    status = "ok"
    snapshot: dict[str, Any] | None = None
    if event == "on_start" and (wf.assign_on_start or wf.assign_force or (wf.comment_on_progress and comment)):
        try:
            raw = jira_request(
                base,
                email,
                token,
                _issue_path(cfg, key),
                query={"fields": "assignee,comment"},
                timeout=timeout,
                urlopen=urlopen,
            )
            snapshot = raw if isinstance(raw, dict) else {}
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: jira issue GET failed: {exc}")
            notes.append(f"issue GET failed: {exc}")
            status = "failed"
    if event == "on_start" and (wf.assign_on_start or wf.assign_force):
        assigned = maybe_assign(cfg, key, urlopen=urlopen, issue=snapshot)
        if assigned.get("note"):
            notes.append(assigned["note"])
        if assigned.get("status") == "failed":
            status = "failed"
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
                notes.append(f"transition {name!r} not found")
                status = "failed"
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
                notes.append(name)
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: jira transition {event} failed: {exc}")
            notes.append(f"transition failed: {exc}")
            status = "failed"
    if wf.comment_on_progress and comment:
        if event == "on_start" and snapshot is not None and _has_started_comment(snapshot, comment):
            notes.append("comment exists")
        else:
            try:
                add_comment(cfg, key, comment, urlopen=urlopen)
                notes.append("commented")
            except Exception as exc:  # noqa: BLE001
                print(f"dev-loop: jira comment failed: {exc}")
                notes.append(f"comment failed: {exc}")
                status = "failed"
    if event == "on_merge":
        try:
            add_to_deploy_ticket(cfg, key, urlopen=urlopen)
        except Exception as exc:  # noqa: BLE001
            print(f"dev-loop: deploy ticket update failed: {exc}")
            notes.append(f"deploy ticket: {exc}")
            status = "failed"
    if status == "ok":
        print(f"dev-loop: jira {event} → {name or 'ok'}")
    note = "; ".join(notes) or event
    return {"event": event, "status": status, "note": note}


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
