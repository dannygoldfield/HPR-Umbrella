#!/usr/bin/env python3
"""Verify locked generator sources and approved visual fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

from hpr_component_paths import component_root, load_component_lock  # noqa: E402


BASELINE_PATH = REPOSITORY_ROOT / "config/approved-visual-baseline.json"
LEGACY_COMPONENT_PATHS = (
    REPOSITORY_ROOT / "components/audio-generator",
    REPOSITORY_ROOT / "components/video-generator",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_approved_visuals(baseline_path: Path = BASELINE_PATH) -> list[str]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    verified: list[str] = []
    for visual in baseline["visuals"]:
        for path_key, hash_key in (
            ("mediaPath", "mediaSha256"),
            ("manifestPath", "manifestSha256"),
        ):
            path = REPOSITORY_ROOT / visual[path_key]
            if not path.is_file():
                raise FileNotFoundError(path)
            actual = _sha256(path)
            if actual != visual[hash_key]:
                raise ValueError(
                    f"{visual['visualId']} {path.name} changed: {actual} != {visual[hash_key]}"
                )
        manifest = json.loads(
            (REPOSITORY_ROOT / visual["manifestPath"]).read_text(encoding="utf-8")
        )
        if not manifest.get("loopSafe") or not manifest.get("geometry", {}).get("fixed"):
            raise ValueError(f"{visual['visualId']} no longer records a fixed, loop-safe visual")
        verified.append(visual["visualId"])
    return verified


def verify_no_embedded_generators() -> None:
    present = [str(path) for path in LEGACY_COMPONENT_PATHS if path.exists()]
    if present:
        raise ValueError(
            "Embedded generator copies are forbidden; use the locked standalone repositories: "
            + ", ".join(present)
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify canonical HPR generator commits and approved visuals"
    )
    parser.add_argument("--sources-only", action="store_true")
    args = parser.parse_args()

    verify_no_embedded_generators()
    print("OK architecture: no embedded generator copies")
    lock = load_component_lock()
    for name in lock["components"]:
        root = component_root(name)
        print(f"OK {name}: {root} @ {lock['components'][name]['commit'][:12]}")
    if not args.sources_only:
        for visual_id in verify_approved_visuals():
            print(f"OK visual: {visual_id}")


if __name__ == "__main__":
    main()
