#!/usr/bin/env python3
"""Render and register the single-source Portrait Development pilot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))
sys.path.insert(0, str(REPOSITORY_ROOT / "components/registry/src"))

from hpr_component_paths import activate_component  # noqa: E402

VIDEO_GENERATOR_ROOT = activate_component("video")

from hpr_registry import (
    initialize_registry,
    list_current_portrait_revisions,
    register_visual_candidate,
)
from hpr_video_generator.config import load_config
from hpr_video_generator.development import (
    DevelopmentCandidate,
    generate_development_candidate,
    load_development_config,
)


def _seed(experiment_id: str, revision_id: str, recipe_id: str) -> int:
    payload = f"{experiment_id}\0{revision_id}\0{recipe_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def render_pilot(
    *,
    db_path: Path,
    output_root: Path,
    generator_config_path: Path,
    development_config_path: Path,
    duration_sec: int,
    ffmpeg: str | None,
) -> dict:
    initialize_registry(db_path)
    generator_config = load_config(generator_config_path)
    development_config = load_development_config(development_config_path)
    revisions = list_current_portrait_revisions(db_path)
    if len(revisions) != 3:
        raise ValueError(f"The pilot requires three portrait revisions; found {len(revisions)}")

    output_root.mkdir(parents=True, exist_ok=True)
    rendered = []
    for revision in revisions:
        portrait_folder = output_root / _slug(revision["original_base_filename"])
        for recipe in development_config.recipes.values():
            visual_id = f"VIS-{revision['portrait_id'].removeprefix('POR-')}-{recipe.id}"
            output = portrait_folder / (
                f"{_slug(revision['original_base_filename'])}__{recipe.id}.mp4"
            )
            seed = _seed(development_config.experiment_id, revision["revision_id"], recipe.id)
            generate_development_candidate(
                generator_config,
                development_config,
                DevelopmentCandidate(
                    portrait_id=revision["portrait_id"],
                    revision_id=revision["revision_id"],
                    portrait=Path(revision["file_path"]),
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
                portrait_id=revision["portrait_id"],
                revision_id=revision["revision_id"],
                motion_recipe_id=recipe.id,
                experiment_id=development_config.experiment_id,
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
                    "portraitId": revision["portrait_id"],
                    "portraitRevisionId": revision["revision_id"],
                    "sourceProject": revision["source_project_display_name"],
                    "sourcePortrait": revision["intake_filename"],
                    "developmentRecipeId": recipe.id,
                    "developmentRecipeName": recipe.name,
                    "developmentMode": recipe.mode,
                    "durationSec": duration_sec,
                    "seed": seed,
                    "video": str(output.resolve()),
                    "manifest": str(manifest_path.resolve()),
                }
            )

    summary = {
        "schemaVersion": "1.0",
        "experimentId": development_config.experiment_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "purpose": "Fixed-geometry portrait surface developing toward the finished source",
        "sourceModel": "single finished source, one-direction reveal",
        "generatorVersion": generator_config.version,
        "developmentConfigVersion": development_config.version,
        "durationSec": duration_sec,
        "portraitCount": len(revisions),
        "recipeCount": len(development_config.recipes),
        "candidateCount": len(rendered),
        "grain": "none",
        "audio": "none",
        "text": "none",
        "candidates": rendered,
    }
    (output_root / "experiment-summary.json").write_text(
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
        default=VIDEO_GENERATOR_ROOT / "config/generator.xml",
    )
    parser.add_argument(
        "--development-config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT / "config/portrait-development-recipes.json",
    )
    parser.add_argument("--duration", type=int, choices=[7, 9, 11], default=7)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    summary = render_pilot(
        db_path=args.db,
        output_root=args.output_root,
        generator_config_path=args.generator_config,
        development_config_path=args.development_config,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
    )
    print(
        f"Rendered and registered {summary['candidateCount']} portrait-development candidates."
    )


if __name__ == "__main__":
    main()
