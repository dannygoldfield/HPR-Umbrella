#!/usr/bin/env python3
"""Render and register a controlled film-grain opacity comparison."""

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

from hpr_registry import (  # noqa: E402
    initialize_registry,
    list_visual_candidates_for_review,
    register_visual_candidate,
)
from hpr_video_generator.film_grain import (  # noqa: E402
    FilmGrainCandidate,
    generate_film_grain_candidate,
    load_film_grain_config,
)


def _seed(*parts: str) -> int:
    payload = "\0".join(parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def render_round(
    *,
    db_path: Path,
    grain_root: Path,
    output_root: Path,
    config_path: Path,
    duration_sec: int,
    ffmpeg: str | None,
    reuse_existing: bool,
) -> dict:
    initialize_registry(db_path)
    config = load_film_grain_config(config_path)
    registered = {
        item["visual_id"]: item for item in list_visual_candidates_for_review(db_path)
    }
    output_root.mkdir(parents=True, exist_ok=True)

    rendered: list[dict] = []
    for base in config.base_visuals:
        parent_visual_id = str(base["visualId"])
        parent = registered.get(parent_visual_id)
        if parent is None:
            raise ValueError(f"Unknown approved base visual: {parent_visual_id}")
        parent_path = Path(parent["media_path"])
        portrait_slug = _slug(parent["original_base_filename"])
        portrait_root = output_root / portrait_slug
        for recipe in config.recipes:
            plate = config.plates.get(recipe.plate_id) if recipe.plate_id else None
            plate_path = grain_root / plate.filename if plate else None
            candidate_seed = _seed(
                config.experiment_id, parent_visual_id, recipe.id
            )
            sample_seed = _seed(
                config.sample_seed_namespace,
                parent_visual_id,
                recipe.plate_id or "control",
            )
            visual_id = f"VIS-{parent['portrait_id'].removeprefix('POR-')}-{recipe.id}"
            output = portrait_root / f"{portrait_slug}__{recipe.id}.mp4"
            manifest_path = output.with_suffix(".json")
            if reuse_existing and output.is_file() and manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                manifest = generate_film_grain_candidate(
                    FilmGrainCandidate(
                        portrait_id=parent["portrait_id"],
                        revision_id=parent["revision_id"],
                        parent_visual_id=parent_visual_id,
                        parent_visual=parent_path,
                        recipe=recipe,
                        plate=plate,
                        plate_path=plate_path,
                        candidate_seed=candidate_seed,
                        sample_seed=sample_seed,
                        duration_sec=duration_sec,
                        output=output,
                    ),
                    ffmpeg=ffmpeg,
                )
                manifest["experimentId"] = config.experiment_id
                manifest["generatorVersion"] = f"film-grain-{config.version}"
                manifest["sourceRights"] = config.source
                manifest["purpose"] = config.purpose
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
                )
            register_visual_candidate(
                db_path,
                visual_id=visual_id,
                portrait_id=parent["portrait_id"],
                revision_id=parent["revision_id"],
                motion_recipe_id=recipe.id,
                experiment_id=config.experiment_id,
                parent_visual_id=parent_visual_id,
                duration_sec=duration_sec,
                seed=candidate_seed,
                generator_version=f"film-grain-{config.version}",
                media_path=output,
                manifest_path=manifest_path,
                status="rendered",
            )
            rendered.append(
                {
                    "visualId": visual_id,
                    "portraitId": parent["portrait_id"],
                    "portraitRevisionId": parent["revision_id"],
                    "portrait": parent["original_base_filename"],
                    "parentVisualId": parent_visual_id,
                    "grainRecipeId": recipe.id,
                    "grainRecipeName": recipe.name,
                    "plate": recipe.plate_id,
                    "opacity": recipe.opacity,
                    "video": str(output.resolve()),
                    "manifest": str(manifest_path.resolve()),
                }
            )

    summary = {
        "schemaVersion": "1.0",
        "experimentId": config.experiment_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "purpose": config.purpose,
        "sampleSeedNamespace": config.sample_seed_namespace,
        "sourceRights": config.source,
        "durationSec": duration_sec,
        "frameRate": 24,
        "frameCount": duration_sec * 24,
        "portraitCount": len(config.base_visuals),
        "recipeCount": len(config.recipes),
        "candidateCount": len(rendered),
        "baseVisualPolicy": "Locked visual is decoded and identically transcoded for every recipe; no development, background, geometry, audio, or text parameter changes.",
        "grainPolicy": "Scanned grain changes luma only. Source plates remain local and are never committed or redistributed.",
        "candidates": rendered,
    }
    (output_root / "experiment-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=REPOSITORY_ROOT / "workspace/registry/hpr.sqlite3",
    )
    parser.add_argument("--grain-root", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "workspace/film-grain-opacity-v25",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT / "config/film-grain-opacity-recipes.json",
    )
    parser.add_argument("--duration", type=int, choices=[11], default=11)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    summary = render_round(
        db_path=args.db,
        grain_root=args.grain_root,
        output_root=args.output_root,
        config_path=args.config,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
        reuse_existing=args.reuse_existing,
    )
    print(
        f"Rendered and registered {summary['candidateCount']} film-grain candidates."
    )


if __name__ == "__main__":
    main()
