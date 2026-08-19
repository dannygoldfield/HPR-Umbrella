#!/usr/bin/env python3
"""Render the five motion rhythms for every current pilot portrait revision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "components/registry/src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "components/video-generator/src"))

from hpr_registry import list_current_portrait_revisions, register_visual_candidate
from hpr_video_generator.config import load_config
from hpr_video_generator.rhythm import (
    RhythmCandidate,
    generate_rhythm_candidate,
    load_rhythm_config,
)


def _seed(revision_id: str, recipe_id: str) -> int:
    payload = f"HPR-motion-pilot-v1\0{revision_id}\0{recipe_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def render_pilot(
    *,
    db_path: Path,
    output_root: Path,
    generator_config_path: Path,
    rhythm_config_path: Path,
    duration_sec: int,
    ffmpeg: str | None,
) -> dict:
    generator_config = load_config(generator_config_path)
    rhythm_config = load_rhythm_config(rhythm_config_path)
    revisions = list_current_portrait_revisions(db_path)
    if not revisions:
        raise ValueError("The Registry has no active portrait revisions")

    output_root.mkdir(parents=True, exist_ok=True)
    rendered = []
    for revision in revisions:
        portrait_id = revision["portrait_id"]
        revision_id = revision["revision_id"]
        portrait_path = Path(revision["file_path"])
        portrait_folder = output_root / _slug(revision["original_base_filename"])
        for recipe in rhythm_config.recipes.values():
            visual_id = f"VIS-{portrait_id.removeprefix('POR-')}-{recipe.id}"
            stem = f"{_slug(revision['original_base_filename'])}__{recipe.id}"
            output = portrait_folder / f"{stem}.mp4"
            seed = _seed(revision_id, recipe.id)
            generate_rhythm_candidate(
                generator_config,
                rhythm_config,
                RhythmCandidate(
                    portrait_id=portrait_id,
                    revision_id=revision_id,
                    portrait=portrait_path,
                    recipe=recipe,
                    seed=seed,
                    duration_sec=duration_sec,
                    output=output,
                ),
                ffmpeg=ffmpeg,
            )
            manifest_path = output.with_suffix(".json")
            register_visual_candidate(
                db_path,
                visual_id=visual_id,
                portrait_id=portrait_id,
                revision_id=revision_id,
                motion_recipe_id=recipe.id,
                experiment_id="motion-rhythm-pilot-v1",
                duration_sec=duration_sec,
                seed=seed,
                generator_version=generator_config.version,
                media_path=output,
                manifest_path=manifest_path,
                status="rendered",
            )
            rendered.append(
                {
                    "visualId": visual_id,
                    "portraitId": portrait_id,
                    "portraitRevisionId": revision_id,
                    "sourceProjectCode": revision["source_project_code"],
                    "sourceProjectDisplayName": revision[
                        "source_project_display_name"
                    ],
                    "sourcePortrait": revision["intake_filename"],
                    "motionRecipeId": recipe.id,
                    "motionRecipeName": recipe.name,
                    "durationSec": duration_sec,
                    "seed": seed,
                    "video": str(output.resolve()),
                    "manifest": str(manifest_path.resolve()),
                }
            )

    summary = {
        "schemaVersion": "1.0",
        "pilot": "HPR three-portrait motion-rhythm pilot",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "generatorVersion": generator_config.version,
        "motionRhythmConfigVersion": rhythm_config.version,
        "durationSec": duration_sec,
        "portraitCount": len(revisions),
        "recipeCount": len(rhythm_config.recipes),
        "candidateCount": len(rendered),
        "grainTreatment": "none",
        "candidates": rendered,
    }
    (output_root / "pilot-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--generator-config",
        type=Path,
        default=REPOSITORY_ROOT / "components/video-generator/config/generator.xml",
    )
    parser.add_argument(
        "--rhythm-config",
        type=Path,
        default=REPOSITORY_ROOT
        / "components/video-generator/config/motion-rhythms.json",
    )
    parser.add_argument("--duration", type=int, choices=[7, 9, 11], default=7)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    summary = render_pilot(
        db_path=args.db,
        output_root=args.output_root,
        generator_config_path=args.generator_config,
        rhythm_config_path=args.rhythm_config,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
    )
    print(
        f"Rendered and registered {summary['candidateCount']} candidates "
        f"for {summary['portraitCount']} portraits."
    )


if __name__ == "__main__":
    main()
