"""Resolve and verify canonical HPR generator repositories.

HPR Umbrella coordinates generator outputs. It must never silently import an
embedded or unexpected copy of either generator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPOSITORY_ROOT / "config/component-lock.json"


class ComponentLockError(RuntimeError):
    """The local generator source does not match Umbrella's production lock."""


def load_component_lock(lock_path: Path = LOCK_PATH) -> dict[str, object]:
    return json.loads(lock_path.read_text(encoding="utf-8"))


def _git(component_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(component_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ComponentLockError(f"Git check failed for {component_root}: {detail}")
    return completed.stdout.strip()


def component_root(
    component: str,
    *,
    verify: bool = True,
    lock_path: Path = LOCK_PATH,
) -> Path:
    lock = load_component_lock(lock_path)
    components = lock.get("components", {})
    if component not in components:
        raise ComponentLockError(f"Unknown component: {component}")
    record = components[component]
    environment_variable = record["environmentVariable"]
    configured = os.environ.get(environment_variable)
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else (REPOSITORY_ROOT / record["localPath"]).resolve()
    )
    if verify:
        verify_component(component, root, record)
    return root


def verify_component(component: str, root: Path, record: dict[str, object]) -> None:
    if not root.is_dir():
        raise ComponentLockError(f"{component} repository is missing: {root}")
    package_path = root / str(record["packagePath"])
    config_path = root / str(record["productionConfig"])
    if not package_path.is_dir() or not config_path.is_file():
        raise ComponentLockError(
            f"{component} repository is incomplete: expected {package_path} and {config_path}"
        )
    remote = _git(root, "remote", "get-url", "origin")
    if remote != record["repository"]:
        raise ComponentLockError(
            f"{component} origin is {remote}; expected {record['repository']}"
        )
    head = _git(root, "rev-parse", "HEAD")
    if head != record["commit"]:
        raise ComponentLockError(
            f"{component} is at {head}; Umbrella is locked to {record['commit']}"
        )
    changes = _git(root, "status", "--porcelain")
    if changes:
        raise ComponentLockError(
            f"{component} has uncommitted changes; production sources must be clean"
        )


def activate_component(component: str, *, verify: bool = True) -> Path:
    """Verify a component and add its canonical src directory to sys.path."""
    import sys

    root = component_root(component, verify=verify)
    source = str(root / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    return root
