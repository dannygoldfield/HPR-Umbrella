#!/usr/bin/env python3
"""Render and register the 11-second, 16-bit TIFF development round."""

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


def _selected_revisions(db_path: Path, intake_config_path: Path) -> list[dict]:
    intake = json.loads(intake_config_path.read_text(encoding="utf-8"))
    filenames = set(intake.get("files", {}))
    if len(filenames) != 3:
        raise ValueError(
            f"The round-two intake config must name exactly three files; found {len(filenames)}"
        )

    current = list_current_portrait_revisions(db_path)
    selected = [
        revision
        for revision in current
        if Path(revision["file_path"]).name in filenames
    ]
    selected_names = {Path(revision["file_path"]).name for revision in selected}
    if selected_names != filenames:
        missing = sorted(filenames - selected_names)
        raise ValueError(f"Current registered TIFF revisions are missing: {missing}")
    if any(Path(revision["file_path"]).suffix.lower() not in {".tif", ".tiff"} for revision in selected):
        raise ValueError("Every round-two source must be a TIFF")

    order = {filename: index for index, filename in enumerate(intake["files"])}
    return sorted(selected, key=lambda item: order[Path(item["file_path"]).name])


def render_round(
    *,
    db_path: Path,
    output_root: Path,
    intake_config_path: Path,
    generator_config_path: Path,
    development_config_path: Path,
    duration_sec: int,
    ffmpeg: str | None,
    reuse_existing: bool = False,
) -> dict:
    initialize_registry(db_path)
    generator_config = load_config(generator_config_path)
    development_config = load_development_config(development_config_path)
    revisions = _selected_revisions(db_path, intake_config_path)
    undersized = [
        (
            Path(revision["file_path"]).name,
            revision["width"],
            revision["height"],
        )
        for revision in revisions
        if revision["width"] < generator_config.width
        or revision["height"] < generator_config.height
    ]
    if undersized:
        details = ", ".join(
            f"{name} ({width}x{height})" for name, width, height in undersized
        )
        raise ValueError(
            "Possible-final sources must meet or exceed the delivery frame "
            f"{generator_config.width}x{generator_config.height}: {details}"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    rendered = []
    for revision in revisions:
        source_name = Path(revision["file_path"]).name
        source_stem = Path(source_name).stem
        portrait_folder = output_root / _slug(source_stem)
        for recipe in development_config.recipes.values():
            visual_id = f"VIS-{revision['portrait_id'].removeprefix('POR-')}-{recipe.id}"
            output = portrait_folder / f"{_slug(source_stem)}__{recipe.id}.mp4"
            seed = _seed(development_config.experiment_id, revision["revision_id"], recipe.id)
            manifest_path = output.with_suffix(".json")
            if not (reuse_existing and output.is_file() and manifest_path.is_file()):
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
                    "sourcePortrait": source_name,
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
        "purpose": "Evaluate speed, easing, and finished-image rests in fixed-geometry portrait development",
        "sourceModel": "native 16-bit TIFF, one-direction reveal toward the finished source",
        "generatorVersion": generator_config.version,
        "developmentConfigVersion": development_config.version,
        "durationSec": duration_sec,
        "frameRate": generator_config.fps,
        "frameCount": duration_sec * generator_config.fps,
        "portraitCount": len(revisions),
        "recipeCount": len(development_config.recipes),
        "candidateCount": len(rendered),
        "grain": "none",
        "audio": "none",
        "text": "none",
        "backgroundExperiment": "deferred",
        "sourceResolutionPolicy": "Every source meets or exceeds the delivery frame; no final candidate begins from an undersized portrait.",
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
        "--intake-config",
        type=Path,
        default=REPOSITORY_ROOT / "workspace/metadata-pilot-v2/expected.json",
    )
    parser.add_argument(
        "--generator-config",
        type=Path,
        default=REPOSITORY_ROOT / "components/video-generator/config/generator.xml",
    )
    parser.add_argument(
        "--development-config",
        type=Path,
        default=REPOSITORY_ROOT
        / "components/video-generator/config/portrait-development-round2-recipes.json",
    )
    parser.add_argument("--duration", type=int, choices=[11], default=11)
    parser.add_argument("--ffmpeg")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse a candidate only when both its video and manifest already exist.",
    )
    args = parser.parse_args()
    summary = render_round(
        db_path=args.db,
        output_root=args.output_root,
        intake_config_path=args.intake_config,
        generator_config_path=args.generator_config,
        development_config_path=args.development_config,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
        reuse_existing=args.reuse_existing,
    )
    print(f"Rendered and registered {summary['candidateCount']} TIFF candidates.")


if __name__ == "__main__":
    main()
