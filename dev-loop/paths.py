#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

PRODUCT = "dev-conductor"
LEGACY_PRODUCT = "mac-ai-setup"
DEV_ROOT_DEFAULT = Path.home() / "dev"


def product_home() -> Path:
    return Path.home() / ".config" / PRODUCT


def legacy_home() -> Path:
    return Path.home() / ".config" / LEGACY_PRODUCT


def migrate_legacy_home() -> None:
    """One-time rename ~/.config/mac-ai-setup -> ~/.config/dev-conductor."""
    new = product_home()
    old = legacy_home()
    if new.exists() or not old.exists():
        return
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)


def config_dir() -> Path:
    override = os.environ.get("DEVLOOP_HOME")
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    migrate_legacy_home()
    p = product_home() / "dev-loop"
    p.mkdir(parents=True, exist_ok=True)
    return p


SECRETS_FILE = product_home() / "secrets.env"
CONFIG_DIR = product_home() / "dev-loop"


def runs_dir() -> Path:
    p = config_dir() / "runs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def memory_dir(slug: str) -> Path:
    p = config_dir() / "memory" / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


def run_dir(key: str) -> Path:
    p = runs_dir() / key.upper()
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_path() -> Path:
    return config_dir() / "state.json"


def secrets_path() -> Path:
    override = os.environ.get("DEV_CONDUCTOR_SECRETS") or os.environ.get("MAC_AI_SETUP_SECRETS")
    if override:
        return Path(override).expanduser()
    migrate_legacy_home()
    return product_home() / "secrets.env"
