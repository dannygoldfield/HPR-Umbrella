#!/usr/bin/env python3
"""Render and register a layered Infinity background comparison."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))
sys.path.insert(0, str(REPOSITORY_ROOT / "components/registry/src"))

from hpr_component_paths import activate_component  # noqa: E402

VIDEO_GENERATOR_ROOT = activate_component("video")

from hpr_registry import (
    initialize_registry,
    list_visual_candidates_for_review,
    register_visual_candidate,
)
from hpr_video_generator.config import load_config
from hpr_video_generator.development import load_development_config
from hpr_video_generator.infinity_background import (
    build_background_context,
    development_state,
    load_infinity_background_config,
    personalize_infinity_background_recipe,
    prepare_layered_working_sources,
    render_background_intermediate,
    render_composite_candidate,
    resolve_font_file,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seed(experiment_id: str, revision_id: str, recipe_id: str) -> int:
    payload = f"{experiment_id}\0{revision_id}\0{recipe_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def render_experiment(
    *,
    db_path: Path,
    output_root: Path,
    layered_tiff: Path,
    subject_png: Path,
    background_png: Path,
    background_config_path: Path,
    development_config_path: Path,
    generator_config_path: Path,
    base_manifest_path: Path,
    duration_sec: int,
    ffmpeg: str,
    reuse_existing: bool = False,
) -> dict:
    initialize_registry(db_path)
    video_config = load_config(generator_config_path)
    background_config = load_infinity_background_config(background_config_path)
    development_config = load_development_config(development_config_path)
    base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))

    base_visual_id = background_config.base_portrait_treatment["visualId"]
    candidates = list_visual_candidates_for_review(db_path)
    base_candidate = next(
        (item for item in candidates if item["visual_id"] == base_visual_id), None
    )
    if base_candidate is None:
        raise ValueError(f"Base visual is not registered: {base_visual_id}")
    development_recipe_id = background_config.base_portrait_treatment[
        "developmentRecipeId"
    ]
    if base_manifest["developmentRecipeId"] != development_recipe_id:
        raise ValueError("Base visual manifest does not match the configured PDE-002 treatment")
    if base_candidate["revision_id"] != base_manifest["portraitRevisionId"]:
        raise ValueError("Base visual and manifest reference different portrait revisions")

    output_root.mkdir(parents=True, exist_ok=True)
    sources = prepare_layered_working_sources(
        layered_tiff=layered_tiff,
        subject_png=subject_png,
        background_png=background_png,
        output_root=output_root / "sources",
        working_width=background_config.working_width,
        working_height=background_config.working_height,
        surrogate_settings=development_config.surrogate,
        ffmpeg=ffmpeg,
    )
    context = build_background_context(
        sources.background_pixels,
        sources.subject_pixels,
        sources.subject_alpha,
    )
    font_record = None
    if background_config.font:
        font_path = resolve_font_file(
            background_config.font["family"],
            background_config.font.get("style", "Regular"),
        )
        context["fontPath"] = str(font_path)
        font_record = {
            "family": background_config.font["family"],
            "style": background_config.font.get("style", "Regular"),
            "localFile": str(font_path.resolve()),
            "localFileSha256": _sha256(font_path),
            "repositoryPolicy": "The locally licensed font file is not copied into the repository.",
        }
    development_recipe = development_config.recipes[development_recipe_id]
    frames = duration_sec * video_config.fps
    focal = base_manifest["field"]["focalPoint"]
    focal_point = (float(focal["x"]), float(focal["y"]))
    development_seed = int(base_manifest["seed"])
    masks, development_timeline, field = development_state(
        recipe=development_recipe,
        development_config=development_config,
        seed=development_seed,
        frames=frames,
        focal_point=focal_point,
    )

    rendered = []
    for configured_recipe in background_config.recipes.values():
        recipe = personalize_infinity_background_recipe(
            configured_recipe,
            base_candidate["portrait_id"],
        )
        recipe_uses_typography = "number" in recipe.effect
        recipe_font_record = font_record if recipe_uses_typography else None
        candidate_seed = _seed(
            background_config.experiment_id,
            base_candidate["revision_id"],
            recipe.id,
        )
        visual_id = (
            f"VIS-{base_candidate['portrait_id'].removeprefix('POR-')}-{recipe.id}"
        )
        background_intermediate = output_root / "backgrounds" / f"{recipe.id}.mkv"
        output = output_root / "candidates" / f"26-Sam-359-LAYERS__{recipe.id}.mp4"
        manifest_path = output.with_suffix(".json")
        if reuse_existing and output.is_file() and manifest_path.is_file():
            background_telemetry = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )["backgroundTelemetry"]
        else:
            background_telemetry = render_background_intermediate(
                recipe=recipe,
                context=context,
                frames=frames,
                fps=video_config.fps,
                output=background_intermediate,
                ffmpeg=ffmpeg,
            )
            render_composite_candidate(
                video_config=video_config,
                subject_finished=sources.subject_finished,
                subject_under_resolved=sources.subject_under_resolved,
                subject_rgba=sources.subject_png,
                background_intermediate=background_intermediate,
                masks=masks,
                mask_width=int(development_config.mask["width"]),
                mask_height=int(development_config.mask["height"]),
                output=output,
                ffmpeg=ffmpeg,
            )
            manifest = {
                "schemaVersion": "1.0",
                "candidateType": "visual_infinity_layered_background",
                "experimentId": background_config.experiment_id,
                "portraitId": base_candidate["portrait_id"],
                "portraitRevisionId": base_candidate["revision_id"],
                "parentVisualId": base_visual_id,
                "basePortraitTreatment": {
                    "visualId": base_visual_id,
                    "developmentRecipeId": development_recipe.id,
                    "developmentRecipeName": development_recipe.name,
                    "developmentConfigVersion": development_config.version,
                    "seed": development_seed,
                    "unchangedAcrossCandidates": True,
                },
                "backgroundRecipeId": recipe.id,
                "backgroundRecipeName": recipe.name,
                "backgroundEffect": recipe.effect,
                "backgroundDescription": recipe.description,
                "backgroundStrength": recipe.strength,
                "backgroundSpeed": recipe.speed,
                "backgroundLoopBehavior": recipe.loop_behavior,
                "backgroundParameters": recipe.parameters,
                "backgroundTypography": recipe_font_record,
                "backgroundVisibilityBoost": recipe.visibility_boost,
                "backgroundPerceptualFloor": recipe.perceptual_floor,
                "backgroundConfigVersion": background_config.version,
                "backgroundPrinciple": background_config.principle,
                "generatorVersion": video_config.version,
                "durationSec": duration_sec,
                "fps": video_config.fps,
                "frames": frames,
                "seed": candidate_seed,
                "loopSafe": recipe.loop_behavior == "continuous",
                "imageOnly": True,
                "audio": "none",
                "grain": "none",
                "text": (
                    "background single digits only; no editorial text"
                    if recipe_uses_typography
                    else "none"
                ),
                "geometry": {
                    "fixed": True,
                    "subjectPositionChange": 0,
                    "subjectScaleChange": 0,
                    "subjectRotationChange": 0,
                    "subjectDisplacement": "none",
                    "backgroundOnlyEffect": True,
                },
                "sourceArtifacts": sources.provenance,
                "field": field,
                "developmentTelemetry": {
                    "visibleInReviewInterface": True,
                    "meaning": "Percentage of untouched finished subject visible in the selected PDE-002 surface treatment",
                    "frameTimeline": development_timeline,
                },
                "backgroundTelemetry": {
                    "visibleInReviewInterface": False,
                    "meaning": "Normalized departure of the background-only layer from the supplied light background",
                    **background_telemetry,
                },
                "intermediateBackground": str(background_intermediate.resolve()),
                "intermediateBackgroundSha256": _sha256(background_intermediate),
                "output": str(output.resolve()),
            }
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

        register_visual_candidate(
            db_path,
            visual_id=visual_id,
            portrait_id=base_candidate["portrait_id"],
            revision_id=base_candidate["revision_id"],
            motion_recipe_id=recipe.id,
            experiment_id=background_config.experiment_id,
            parent_visual_id=base_visual_id,
            duration_sec=duration_sec,
            seed=candidate_seed,
            generator_version=video_config.version,
            media_path=output,
            manifest_path=manifest_path,
            status="rendered",
        )
        rendered.append(
            {
                "visualId": visual_id,
                "parentVisualId": base_visual_id,
                "portraitId": base_candidate["portrait_id"],
                "portraitRevisionId": base_candidate["revision_id"],
                "backgroundRecipeId": recipe.id,
                "backgroundRecipeName": recipe.name,
                "backgroundEffect": recipe.effect,
                "video": str(output.resolve()),
                "manifest": str(manifest_path.resolve()),
            }
        )

    typography_count = sum(
        "number" in recipe.effect for recipe in background_config.recipes.values()
    )
    summary = {
        "schemaVersion": "1.0",
        "experimentId": background_config.experiment_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "purpose": background_config.principle,
        "baseVisualId": base_visual_id,
        "baseDevelopmentRecipeId": development_recipe.id,
        "durationSec": duration_sec,
        "frameRate": video_config.fps,
        "frameCount": frames,
        "candidateCount": len(rendered),
        "grain": "none",
        "audio": "none",
        "text": (
            f"background single digits in {typography_count} candidates; "
            "no editorial text"
        ),
        "subjectGeometry": "fixed",
        "loopBehavior": "per candidate; continuous or intentional hard reset",
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
    parser.add_argument("--layered-tiff", type=Path, required=True)
    parser.add_argument("--subject-png", type=Path, required=True)
    parser.add_argument("--background-png", type=Path, required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument(
        "--background-config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT / "config/infinity-background-recipes.json",
    )
    parser.add_argument(
        "--development-config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT
        / "config/portrait-development-settlement-recipes.json",
    )
    parser.add_argument(
        "--generator-config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT / "config/generator.xml",
    )
    parser.add_argument(
        "--base-manifest",
        type=Path,
        default=REPOSITORY_ROOT
        / "workspace/portrait-development-settlement-v9/26-Sam-359/26-Sam-359__PDE-002.json",
    )
    parser.add_argument("--duration", type=int, choices=[11], default=11)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    summary = render_experiment(
        db_path=args.db,
        output_root=args.output_root,
        layered_tiff=args.layered_tiff,
        subject_png=args.subject_png,
        background_png=args.background_png,
        background_config_path=args.background_config,
        development_config_path=args.development_config,
        generator_config_path=args.generator_config,
        base_manifest_path=args.base_manifest,
        duration_sec=args.duration,
        ffmpeg=args.ffmpeg,
        reuse_existing=args.reuse_existing,
    )
    print(f"Rendered and registered {summary['candidateCount']} Infinity backgrounds.")


if __name__ == "__main__":
    main()
