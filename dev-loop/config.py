#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mini_yaml import loads
from paths import DEV_ROOT_DEFAULT, config_dir, secrets_path

EXAMPLE_JQL = (
    "assignee = currentUser() AND sprint in openSprints() "
    "AND statusCategory != Done"
)


def _d(data: dict, *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return default if cur is None else cur


def _str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    return [str(val)]


@dataclass
class JiraCfg:
    project: str = ""
    jql: str = EXAMPLE_JQL
    base_url: str = ""
    auth: str = "basic"  # basic | none
    search_path: str = "/rest/api/3/search/jql"
    issue_path: str = "/rest/api/3/issue/{key}"
    fields: str = "summary,description,status,issuetype,comment,labels"
    max_keys: int = 15
    timeout_sec: int = 20
    comment_limit: int = 8


@dataclass
class GitCfg:
    require_github_remote: bool = True
    allow_outside_dev: bool = False
    never_commit_branches: list[str] = field(default_factory=lambda: ["main", "master"])
    branch_pattern: str = "feat/{key}-{slug}"
    commit_type: str = "feat"
    slug_max_len: int = 40
    push: bool = True
    create_pr: bool = True
    gh_bin: str = "gh"
    pr_title_pattern: str = "{type}: {summary} ({key})"
    merge_to_default_after_ship: bool = False
    check_conventional: bool = True
    rewrite_unpushed: bool = True
    stack_prs: bool = False
    max_files_per_pr: int = 0
    merge_method: str = "squash"


@dataclass
class RuntimeCfg:
    agent: str = "claude"  # claude | cursor | none
    launch_script: str = ""
    wait_timeout_sec: int = 86400
    poll_interval_sec: int = 2
    no_launch: bool = False
    builtin_adapters: bool = False
    auto_continue: bool = False


@dataclass
class CapsCfg:
    writer_retries: int = 3
    review_retries: int = 3


@dataclass
class ReviewCfg:
    pass_verdicts: list[str] = field(default_factory=lambda: ["excellent", "good"])
    rewrite_verdicts: list[str] = field(
        default_factory=lambda: ["good-with-risks", "needs_improvement", "blocker"]
    )
    default_verdict: str = "good"


@dataclass
class SessionStartCfg:
    enabled: bool = True
    cache_minutes: int = 10
    keys_limit: int = 15
    print_keys: bool = True


@dataclass
class RepoPickCfg:
    max_depth: int = 3
    max_choices: int = 40
    ask_when_cwd_not_repo: bool = True
    skip: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "dist",
            "build",
            "target",
            "__pycache__",
            "venv",
            ".venv",
            ".tox",
            "coverage",
        ]
    )
    create_private: bool = True
    gh_create: bool = True


@dataclass
class MemoryCfg:
    max_contract_files: int = 24
    max_contract_lines: int = 80
    contract_globs: list[str] = field(
        default_factory=lambda: [
            "*Controller*",
            "*Resource.java",
            "*Api.java",
            "*Client.java",
            "openapi*.yaml",
            "openapi*.yml",
            "openapi*.json",
            "*openapi*",
            "*.proto",
        ]
    )


@dataclass
class SnykCfg:
    enabled: bool = False
    required: bool = False
    cmd: str = "snyk test --json"
    fail_on: str = "high"


@dataclass
class SonarCfg:
    enabled: bool = False
    required: bool = False
    cmd: str = "sonar-scanner"


@dataclass
class MutationCfg:
    enabled: bool = False
    required: bool = False
    cmd: str = ""
    # killed = PIT mutants killed (default, higher is better). survived = 100-killed,
    # treated as a ceiling (lower is better). "98% survived" is almost certainly inverted.
    metric: str = "killed"
    min_pct: float = 75.0


@dataclass
class QualityCfg:
    snyk: SnykCfg = None  # type: ignore[assignment]
    sonar: SonarCfg = None  # type: ignore[assignment]
    mutation: MutationCfg = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.snyk is None:
            self.snyk = SnykCfg()
        if self.sonar is None:
            self.sonar = SonarCfg()
        if self.mutation is None:
            self.mutation = MutationCfg()


@dataclass
class EvidenceCfg:
    enabled: bool = False
    mode: str = "http"
    timeout_sec: int = 8
    probes: list = None  # type: ignore[assignment]
    playwright_cmd: str = ""

    def __post_init__(self) -> None:
        if self.probes is None:
            self.probes = []


@dataclass
class PollerCfg:
    enabled: bool = False
    interval_minutes: int = 30
    auto_merge: bool = False
    on_comments: str = "fix"
    on_checks_failed: str = "fix"
    bot_logins: list = None  # type: ignore[assignment]
    notify: bool = True
    merge_method: str = "squash"

    def __post_init__(self) -> None:
        if self.bot_logins is None:
            self.bot_logins = []


@dataclass
class WorkflowCfg:
    enabled: bool = False
    on_start: str = "In Progress"
    on_pr: str = "In Review"
    on_merge: str = "Done"
    on_block: str = "Blocked"
    on_waiting: str = "Waiting"
    deploy_ticket_jql: str = ""
    deploy_ticket_key: str = ""
    comment_on_progress: bool = True


@dataclass
class AutonomyCfg:
    # supervised = human spec gate. unattended = spec auto-approved and continue with no operator.
    profile: str = "supervised"
    spec_approval: str = "human"  # human | auto
    continue_after_spec: bool = False
    merge: str = "alert"  # alert | auto | off
    ask_repo: bool = True


@dataclass
class DevLoopConfig:
    mode: str = "prod"  # prod | test
    dev_root: Path = DEV_ROOT_DEFAULT
    allowlist: list[str] = field(default_factory=list)
    denylist: list[str] = field(default_factory=list)
    health: dict[str, str] = field(default_factory=dict)
    verify: dict[str, dict[str, str]] = field(default_factory=dict)
    verify_fail_closed: bool = True
    verify_timeout_sec: int = 1800
    jira: JiraCfg = field(default_factory=JiraCfg)
    git: GitCfg = field(default_factory=GitCfg)
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)
    caps: CapsCfg = field(default_factory=CapsCfg)
    review: ReviewCfg = field(default_factory=ReviewCfg)
    session_start: SessionStartCfg = field(default_factory=SessionStartCfg)
    memory: MemoryCfg = field(default_factory=MemoryCfg)
    spec_auto_approve: bool = False
    repo_pick: RepoPickCfg = field(default_factory=RepoPickCfg)
    quality: QualityCfg = field(default_factory=QualityCfg)
    evidence: EvidenceCfg = field(default_factory=EvidenceCfg)
    poller: PollerCfg = field(default_factory=PollerCfg)
    workflow: WorkflowCfg = field(default_factory=WorkflowCfg)
    autonomy: AutonomyCfg = field(default_factory=AutonomyCfg)
    stages_enabled: dict[str, bool] = field(
        default_factory=lambda: {
            "spec": True,
            "test_writer": True,
            "writer": True,
            "verify": True,
            "review": True,
            "simplify": False,
            "ship": True,
        }
    )

    @property
    def jira_project(self) -> str:
        return self.jira.project

    @property
    def jql(self) -> str:
        jql = self.jira.jql
        project = self.jira.project
        if project and "project =" not in jql.lower():
            return f"project = {project} AND ({jql})"
        return jql

    @property
    def cache_minutes(self) -> int:
        return self.session_start.cache_minutes


def load_secrets(path: Path | None = None) -> dict[str, str]:
    p = path or secrets_path()
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export ") :]
        if "=" not in s:
            continue
        k, _, v = s.partition("=")
        v = v.strip().strip("'").strip('"')
        out[k.strip()] = v
    for key in (
        "ATLASSIAN_BASE_URL",
        "ATLASSIAN_EMAIL",
        "ATLASSIAN_API_TOKEN",
        "ATLASSIAN_JIRA_PROJECT",
        "DEVLOOP_CONFIG",
    ):
        if os.environ.get(key):
            out[key] = os.environ[key]
    return out


def jira_creds(cfg: DevLoopConfig | None = None, secrets: dict[str, str] | None = None) -> tuple[str, str, str]:
    s = secrets if secrets is not None else load_secrets()
    cfg = cfg or load_config()
    base = (cfg.jira.base_url or s.get("ATLASSIAN_BASE_URL") or "").rstrip("/")
    email = s.get("ATLASSIAN_EMAIL") or ""
    token = s.get("ATLASSIAN_API_TOKEN") or ""
    if cfg.jira.auth == "none":
        if not base:
            raise SystemExit("dev-loop: jira.base_url required when jira.auth is none")
        return base, email or "devloop@local", token or "none"
    if not base or not email or not token or "__SET_ME__" in (base + email + token):
        raise SystemExit(
            "dev-loop: fill ATLASSIAN_BASE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN "
            f"in {secrets_path()} or set jira.base_url / jira.auth in config."
        )
    return base, email, token


def load_config(path: Path | None = None) -> DevLoopConfig:
    env_cfg = os.environ.get("DEVLOOP_CONFIG")
    cfg_path = path or (Path(env_cfg).expanduser() if env_cfg else config_dir() / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.is_file():
        parsed = loads(cfg_path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            data = parsed
    secrets = load_secrets()
    jira_d = data.get("jira") if isinstance(data.get("jira"), dict) else {}
    git_d = data.get("git") if isinstance(data.get("git"), dict) else {}
    rt_d = data.get("runtime") if isinstance(data.get("runtime"), dict) else {}
    caps_d = data.get("caps") if isinstance(data.get("caps"), dict) else {}
    rev_d = data.get("review") if isinstance(data.get("review"), dict) else {}
    ss_d = data.get("session_start") if isinstance(data.get("session_start"), dict) else {}
    mem_d = data.get("memory") if isinstance(data.get("memory"), dict) else {}
    stages_d = data.get("stages") if isinstance(data.get("stages"), dict) else {}
    q_d = data.get("quality") if isinstance(data.get("quality"), dict) else {}
    ev_d = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    pol_d = data.get("poller") if isinstance(data.get("poller"), dict) else {}
    wf_d = data.get("workflow") if isinstance(data.get("workflow"), dict) else {}
    aut_d = data.get("autonomy") if isinstance(data.get("autonomy"), dict) else {}
    snyk_d = q_d.get("snyk") if isinstance(q_d.get("snyk"), dict) else {}
    sonar_d = q_d.get("sonar") if isinstance(q_d.get("sonar"), dict) else {}
    mut_d = q_d.get("mutation") if isinstance(q_d.get("mutation"), dict) else {}
    verify = data.get("verify") if isinstance(data.get("verify"), dict) else {}
    health = data.get("health") if isinstance(data.get("health"), dict) else {}
    repo_d = data.get("repo") if isinstance(data.get("repo"), dict) else {}

    project = str(
        jira_d.get("project") or secrets.get("ATLASSIAN_JIRA_PROJECT") or ""
    ).strip()
    jql = str(jira_d.get("jql") or EXAMPLE_JQL)
    launch_default = str(Path.home() / ".claude" / "hooks" / "prompt-enrich" / "launch-clean-claude.sh")

    enabled = {
        "spec": True,
        "test_writer": True,
        "writer": True,
        "verify": True,
        "review": True,
        "simplify": False,
        "ship": True,
    }
    for k, v in stages_d.items():
        if isinstance(v, dict) and "enabled" in v:
            enabled[str(k)] = bool(v["enabled"])
        elif isinstance(v, bool):
            enabled[str(k)] = v

    spec_auto = bool(_d(stages_d, "spec", "auto_approve", default=False) or data.get("spec_auto_approve"))

    cfg = DevLoopConfig(
        mode=str(data.get("mode") or "prod"),
        dev_root=Path(os.path.expanduser(str(data.get("dev_root") or DEV_ROOT_DEFAULT))),
        allowlist=_str_list(repo_d.get("allowlist") or data.get("allowlist")),
        denylist=_str_list(repo_d.get("denylist") or data.get("denylist")),
        health={str(k): str(v) for k, v in health.items()},
        verify={
            str(k): {str(ik): str(iv) for ik, iv in (v or {}).items()}
            for k, v in verify.items()
            if isinstance(v, dict)
        },
        verify_fail_closed=bool(data.get("verify_fail_closed", True)),
        verify_timeout_sec=int(_d(data, "verify_timeout_sec", default=1800) or 1800),
        jira=JiraCfg(
            project=project,
            jql=jql,
            base_url=str(jira_d.get("base_url") or ""),
            auth=str(jira_d.get("auth") or "basic"),
            search_path=str(jira_d.get("search_path") or "/rest/api/3/search/jql"),
            issue_path=str(jira_d.get("issue_path") or "/rest/api/3/issue/{key}"),
            fields=str(jira_d.get("fields") or "summary,description,status,issuetype,comment,labels"),
            max_keys=int(jira_d.get("max_keys") or 15),
            timeout_sec=int(jira_d.get("timeout_sec") or 20),
            comment_limit=int(jira_d.get("comment_limit") or 8),
        ),
        git=GitCfg(
            require_github_remote=bool(git_d.get("require_github_remote", True)),
            allow_outside_dev=bool(git_d.get("allow_outside_dev", False)),
            never_commit_branches=_str_list(git_d.get("never_commit_branches") or ["main", "master"]),
            branch_pattern=str(git_d.get("branch_pattern") or "feat/{key}-{slug}"),
            commit_type=str(git_d.get("commit_type") or "feat"),
            slug_max_len=int(git_d.get("slug_max_len") or 40),
            push=bool(git_d.get("push", True)),
            create_pr=bool(git_d.get("create_pr", True)),
            gh_bin=str(git_d.get("gh_bin") or "gh"),
            pr_title_pattern=str(git_d.get("pr_title_pattern") or "{type}: {summary} ({key})"),
            merge_to_default_after_ship=bool(git_d.get("merge_to_default_after_ship", False)),
            check_conventional=bool(git_d.get("check_conventional", True)),
            rewrite_unpushed=bool(git_d.get("rewrite_unpushed", True)),
            stack_prs=bool(git_d.get("stack_prs", False)),
            max_files_per_pr=int(git_d.get("max_files_per_pr") or 0),
            merge_method=str(git_d.get("merge_method") or "squash"),
        ),
        runtime=RuntimeCfg(
            agent=str(rt_d.get("agent") or "claude"),
            launch_script=str(rt_d.get("launch_script") or launch_default),
            wait_timeout_sec=int(rt_d.get("wait_timeout_sec") or 86400),
            poll_interval_sec=int(rt_d.get("poll_interval_sec") or 2),
            no_launch=bool(rt_d.get("no_launch", False)),
            builtin_adapters=bool(rt_d.get("builtin_adapters", False)),
            auto_continue=bool(rt_d.get("auto_continue", False)),
        ),
        caps=CapsCfg(
            writer_retries=int(caps_d.get("writer_retries") or 3),
            review_retries=int(caps_d.get("review_retries") or 3),
        ),
        review=ReviewCfg(
            pass_verdicts=_str_list(rev_d.get("pass_verdicts") or ["excellent", "good"]),
            rewrite_verdicts=_str_list(
                rev_d.get("rewrite_verdicts")
                or ["good-with-risks", "needs_improvement", "blocker"]
            ),
            default_verdict=str(rev_d.get("default_verdict") or "good"),
        ),
        session_start=SessionStartCfg(
            enabled=bool(ss_d.get("enabled", True)),
            cache_minutes=int(ss_d.get("cache_minutes") or data.get("cache_minutes") or 10),
            keys_limit=int(ss_d.get("keys_limit") or 15),
            print_keys=bool(ss_d.get("print_keys", True)),
        ),
        memory=MemoryCfg(
            max_contract_files=int(mem_d.get("max_contract_files") or 24),
            max_contract_lines=int(mem_d.get("max_contract_lines") or 80),
            contract_globs=_str_list(mem_d.get("contract_globs"))
            or MemoryCfg().contract_globs,
        ),
        spec_auto_approve=spec_auto,
        repo_pick=RepoPickCfg(
            max_depth=int(repo_d.get("max_depth") or 3),
            max_choices=int(repo_d.get("max_choices") or 40),
            ask_when_cwd_not_repo=bool(repo_d.get("ask_when_cwd_not_repo", True)),
            skip=_str_list(repo_d.get("skip")) or RepoPickCfg().skip,
            create_private=bool(repo_d.get("create_private", True)),
            gh_create=bool(repo_d.get("gh_create", True)),
        ),
        quality=QualityCfg(
            snyk=SnykCfg(
                enabled=bool(snyk_d.get("enabled", False)),
                required=bool(snyk_d.get("required", False)),
                cmd=str(snyk_d.get("cmd") or "snyk test --json"),
                fail_on=str(snyk_d.get("fail_on") or "high"),
            ),
            sonar=SonarCfg(
                enabled=bool(sonar_d.get("enabled", False)),
                required=bool(sonar_d.get("required", False)),
                cmd=str(sonar_d.get("cmd") or "sonar-scanner"),
            ),
            mutation=MutationCfg(
                enabled=bool(mut_d.get("enabled", False)),
                required=bool(mut_d.get("required", False)),
                cmd=str(mut_d.get("cmd") or ""),
                metric=str(mut_d.get("metric") or "killed"),
                min_pct=float(mut_d.get("min_pct") or 75),
            ),
        ),
        evidence=EvidenceCfg(
            enabled=bool(ev_d.get("enabled", False)),
            mode=str(ev_d.get("mode") or "http"),
            timeout_sec=int(ev_d.get("timeout_sec") or 8),
            probes=list(ev_d.get("probes") or []) if isinstance(ev_d.get("probes"), list) else [],
            playwright_cmd=str(ev_d.get("playwright_cmd") or ""),
        ),
        poller=PollerCfg(
            enabled=bool(pol_d.get("enabled", False)),
            interval_minutes=int(pol_d.get("interval_minutes") or 30),
            auto_merge=bool(pol_d.get("auto_merge", False)),
            on_comments=str(pol_d.get("on_comments") or "fix"),
            on_checks_failed=str(pol_d.get("on_checks_failed") or "fix"),
            bot_logins=_str_list(pol_d.get("bot_logins")),
            notify=bool(pol_d.get("notify", True)),
            merge_method=str(pol_d.get("merge_method") or git_d.get("merge_method") or "squash"),
        ),
        workflow=WorkflowCfg(
            enabled=bool(wf_d.get("enabled", False)),
            on_start=str(wf_d.get("on_start") or "In Progress"),
            on_pr=str(wf_d.get("on_pr") or "In Review"),
            on_merge=str(wf_d.get("on_merge") or "Done"),
            on_block=str(wf_d.get("on_block") or "Blocked"),
            on_waiting=str(wf_d.get("on_waiting") or "Waiting"),
            deploy_ticket_jql=str(wf_d.get("deploy_ticket_jql") or ""),
            deploy_ticket_key=str(wf_d.get("deploy_ticket_key") or ""),
            comment_on_progress=bool(wf_d.get("comment_on_progress", True)),
        ),
        stages_enabled=enabled,
        autonomy=AutonomyCfg(
            profile=str(aut_d.get("profile") or "supervised"),
            spec_approval=str(aut_d.get("spec_approval") or ""),
            continue_after_spec=bool(aut_d.get("continue_after_spec", False)),
            merge=str(aut_d.get("merge") or ""),
            ask_repo=bool(aut_d.get("ask_repo", True)),
        ),
    )
    return _apply_autonomy(cfg)


def _apply_autonomy(cfg: DevLoopConfig) -> DevLoopConfig:
    profile = (cfg.autonomy.profile or "supervised").lower()
    unattended = profile == "unattended"
    if unattended:
        spec = "auto"
        cont = True
        ask = False
    else:
        spec = cfg.autonomy.spec_approval or "human"
        cont = bool(cfg.autonomy.continue_after_spec)
        ask = bool(cfg.autonomy.ask_repo)
    merge = cfg.autonomy.merge or "alert"
    cfg.autonomy.spec_approval = spec
    cfg.autonomy.continue_after_spec = cont
    cfg.autonomy.merge = merge or "alert"
    cfg.autonomy.ask_repo = ask
    if spec == "auto":
        cfg.spec_auto_approve = True
    if cont:
        cfg.runtime.auto_continue = True
    if not ask:
        cfg.repo_pick.ask_when_cwd_not_repo = False
    if merge == "auto":
        cfg.poller.auto_merge = True
    return cfg


def example_yaml() -> str:
    return (Path(__file__).parent / "config.yaml.example").read_text(encoding="utf-8")
