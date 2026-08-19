#!/usr/bin/env python3
"""Render the image-only white-balance calibration pilot."""

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

from hpr_registry import (
    initialize_registry,
    list_current_portrait_revisions,
    register_visual_candidate,
)
from hpr_video_generator.config import load_config
from hpr_video_generator.white_balance import (
    WhiteBalanceCandidate,
    generate_white_balance_candidate,
    load_white_balance_config,
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
    white_balance_config_path: Path,
    duration_sec: int,
    ffmpeg: str | None,
) -> dict:
    initialize_registry(db_path)
    generator_config = load_config(generator_config_path)
    wb_config = load_white_balance_config(white_balance_config_path)
    experiment_id = wb_config.experiment_id
    revisions = list_current_portrait_revisions(db_path)
    if len(revisions) != 3:
        raise ValueError(f"The pilot requires three portrait revisions; found {len(revisions)}")

    output_root.mkdir(parents=True, exist_ok=True)
    rendered = []
    for revision in revisions:
        portrait_folder = output_root / _slug(revision["original_base_filename"])
        for recipe in wb_config.recipes.values():
            visual_id = (
                f"VIS-{revision['portrait_id'].removeprefix('POR-')}-{recipe.id}"
            )
            output = portrait_folder / (
                f"{_slug(revision['original_base_filename'])}__{recipe.id}.mp4"
            )
            seed = _seed(experiment_id, revision["revision_id"], recipe.id)
            generate_white_balance_candidate(
                generator_config,
                wb_config,
                WhiteBalanceCandidate(
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
                experiment_id=experiment_id,
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
                    "whiteBalanceRecipeId": recipe.id,
                    "whiteBalanceRecipeName": recipe.name,
                    "adjustmentType": recipe.adjustment_type,
                    "durationSec": duration_sec,
                    "seed": seed,
                    "video": str(output.resolve()),
                    "manifest": str(manifest_path.resolve()),
                    "commands": str(output.with_suffix(".commands.txt").resolve()),
                }
            )

    summary = {
        "schemaVersion": "1.0",
        "experimentId": experiment_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "purpose": "Image-only animation inspired by manual white-balance adjustment",
        "generatorVersion": generator_config.version,
        "whiteBalanceConfigVersion": wb_config.version,
        "durationSec": duration_sec,
        "portraitCount": len(revisions),
        "recipeCount": len(wb_config.recipes),
        "candidateCount": len(rendered),
        "interfaceTelemetry": "Temperature and Tint sliders outside the video",
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
        default=REPOSITORY_ROOT / "components/video-generator/config/generator.xml",
    )
    parser.add_argument(
        "--white-balance-config",
        type=Path,
        default=REPOSITORY_ROOT
        / "components/video-generator/config/white-balance-recipes.json",
    )
    parser.add_argument("--duration", type=int, choices=[7, 9, 11], default=7)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    summary = render_pilot(
        db_path=args.db,
        output_root=args.output_root,
        generator_config_path=args.generator_config,
        white_balance_config_path=args.white_balance_config,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
    )
    print(
        f"Rendered and registered {summary['candidateCount']} white-balance candidates."
    )


if __name__ == "__main__":
    main()
