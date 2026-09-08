#!/usr/bin/env python3
"""Render one-variable motion probes from each selected pilot rhythm."""

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
    list_visual_candidates_for_review,
    register_visual_candidate,
)
from hpr_video_generator.config import load_config
from hpr_video_generator.experiments import derive_motion_variable_variants
from hpr_video_generator.rhythm import (
    RhythmCandidate,
    generate_rhythm_candidate,
    load_rhythm_config,
)


EXPERIMENT_ID = "motion-variable-pilot-v2"
REFERENCE_EXPERIMENT_ID = "motion-rhythm-pilot-v1"


def _seed(revision_id: str, recipe_id: str) -> int:
    payload = f"{EXPERIMENT_ID}\0{revision_id}\0{recipe_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def render_experiment(
    *,
    db_path: Path,
    output_root: Path,
    generator_config_path: Path,
    rhythm_config_path: Path,
    ffmpeg: str | None,
) -> dict:
    initialize_registry(db_path)
    generator_config = load_config(generator_config_path)
    rhythm_config = load_rhythm_config(rhythm_config_path)
    review_candidates = list_visual_candidates_for_review(db_path)
    references = [
        candidate
        for candidate in review_candidates
        if candidate["experiment_id"] == REFERENCE_EXPERIMENT_ID
        and candidate["selected"]
    ]
    by_portrait: dict[str, list[dict]] = {}
    for reference in references:
        by_portrait.setdefault(reference["portrait_id"], []).append(reference)
    ambiguous = {
        portrait_id: rows
        for portrait_id, rows in by_portrait.items()
        if len(rows) != 1
    }
    if len(by_portrait) != 3 or ambiguous:
        raise ValueError(
            "The experiment requires exactly one selected V1 reference for each "
            f"of three portraits; found {len(references)} selections"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    rendered = []
    reference_summary = []
    for reference in references:
        base_recipe = rhythm_config.recipes.get(reference["motion_recipe_id"])
        if not base_recipe:
            raise ValueError(
                f"Reference {reference['visual_id']} uses an unknown rhythm recipe"
            )
        reference_summary.append(
            {
                "visualId": reference["visual_id"],
                "portraitId": reference["portrait_id"],
                "sourcePortrait": reference["intake_filename"],
                "motionRecipeId": base_recipe.id,
                "video": reference["media_path"],
            }
        )
        # The visual manifest carries the immutable source JPEG path.
        reference_manifest = json.loads(Path(reference["manifest_path"]).read_text())
        source_portrait_path = Path(reference_manifest["portrait"])
        portrait_folder = output_root / _slug(reference["original_base_filename"])
        for variant in derive_motion_variable_variants(base_recipe):
            recipe = variant.recipe
            visual_id = (
                f"VIS-{reference['portrait_id'].removeprefix('POR-')}-{recipe.id}"
            )
            output = portrait_folder / (
                f"{_slug(reference['original_base_filename'])}__{recipe.id}.mp4"
            )
            seed = _seed(reference["revision_id"], recipe.id)
            candidate = RhythmCandidate(
                portrait_id=reference["portrait_id"],
                revision_id=reference["revision_id"],
                portrait=source_portrait_path,
                recipe=recipe,
                seed=seed,
                duration_sec=int(reference["duration_sec"]),
                output=output,
                experiment_id=EXPERIMENT_ID,
                parent_visual_id=reference["visual_id"],
                experiment_variables=variant.parameters,
            )
            generate_rhythm_candidate(
                generator_config,
                rhythm_config,
                candidate,
                ffmpeg=ffmpeg,
            )
            manifest_path = output.with_suffix(".json")
            register_visual_candidate(
                db_path,
                visual_id=visual_id,
                portrait_id=reference["portrait_id"],
                revision_id=reference["revision_id"],
                motion_recipe_id=recipe.id,
                experiment_id=EXPERIMENT_ID,
                parent_visual_id=reference["visual_id"],
                duration_sec=reference["duration_sec"],
                seed=seed,
                generator_version=generator_config.version,
                media_path=output,
                manifest_path=manifest_path,
                status="rendered",
            )
            rendered.append(
                {
                    "visualId": visual_id,
                    "parentVisualId": reference["visual_id"],
                    "portraitId": reference["portrait_id"],
                    "portraitRevisionId": reference["revision_id"],
                    "sourcePortrait": reference["intake_filename"],
                    "motionRecipeId": recipe.id,
                    "motionRecipeName": recipe.name,
                    "variable": variant.variable,
                    "parameters": variant.parameters,
                    "durationSec": reference["duration_sec"],
                    "seed": seed,
                    "video": str(output.resolve()),
                    "manifest": str(manifest_path.resolve()),
                }
            )

    summary = {
        "schemaVersion": "1.0",
        "experimentId": EXPERIMENT_ID,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "purpose": "Change one motion dimension at a time from selected V1 rhythms",
        "generatorVersion": generator_config.version,
        "motionRhythmConfigVersion": rhythm_config.version,
        "referenceCount": len(reference_summary),
        "newCandidateCount": len(rendered),
        "comparisonCount": len(reference_summary) + len(rendered),
        "grainTreatment": "none",
        "references": reference_summary,
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
        "--rhythm-config",
        type=Path,
        default=VIDEO_GENERATOR_ROOT / "config/motion-rhythms.json",
    )
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    summary = render_experiment(
        db_path=args.db,
        output_root=args.output_root,
        generator_config_path=args.generator_config,
        rhythm_config_path=args.rhythm_config,
        ffmpeg=args.ffmpeg,
    )
    print(
        f"Rendered {summary['newCandidateCount']} new candidates; "
        f"the review set has {summary['comparisonCount']} comparisons."
    )


if __name__ == "__main__":
    main()
