#!/usr/bin/env python3
"""Generate and register ten native 11-second audio/visual pair candidates."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import wave


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "components/audio-generator/src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "components/registry/src"))

from hpr_audio_generator.config import Config, load_config  # noqa: E402
from hpr_audio_generator.generator import generate  # noqa: E402
from hpr_registry import (  # noqa: E402
    initialize_registry,
    list_visual_candidates_for_review,
    register_audio_candidate,
    register_pair_candidate,
)


EXPERIMENT_ID = "pairing-nychildren-v27"
DEFAULT_VISUAL_ID = "VIS-30FE48FB73CE-PDE-002"
DEFAULT_RECIPE_ID = "AR-010"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\0".join(map(str, parts)).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12].upper()}"


def _seed_base(*parts: object) -> int:
    payload = "\0".join(map(str, parts)).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def _eligible_assets(config: Config, recipe_id: str) -> tuple[list, list]:
    recipe = config.recipes[recipe_id]
    beds = [
        asset
        for asset in config.assets
        if asset.role == "Bed"
        and asset.status == "Active"
        and (recipe.bed_family is None or asset.family == recipe.bed_family)
    ]
    gestures = [
        asset
        for asset in config.assets
        if asset.role == "Gesture"
        and asset.status == "Active"
        and (recipe.gesture_family is None or asset.family == recipe.gesture_family)
    ]
    if not beds or not gestures:
        raise ValueError(f"{recipe_id} has no eligible bed or gesture")
    return beds, gestures


def distinct_seeds(
    config: Config,
    recipe_id: str,
    count: int,
    base_seed: int,
) -> list[int]:
    """Choose deterministic seeds with distinct bed/gesture combinations."""
    beds, gestures = _eligible_assets(config, recipe_id)
    available = len(beds) * len(gestures)
    if count > available:
        raise ValueError(f"Requested {count} candidates but only {available} unique pairs exist")
    seeds: list[int] = []
    ingredients: set[tuple[str, str]] = set()
    offset = 0
    while len(seeds) < count:
        seed = base_seed + offset
        rng = random.Random(seed)
        ingredient = (rng.choice(beds).asset_id, rng.choice(gestures).asset_id)
        if ingredient not in ingredients:
            ingredients.add(ingredient)
            seeds.append(seed)
        offset += 1
        if offset > available * 100:
            raise RuntimeError("Could not find enough distinct deterministic ingredients")
    return seeds


def _asset(config: Config, asset_id: str):
    return next(asset for asset in config.assets if asset.asset_id == asset_id)


def _probe(ffprobe: str, path: Path) -> dict:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _validate_wav(path: Path, config: Config, duration_sec: int) -> None:
    with wave.open(str(path), "rb") as source:
        actual = (
            source.getframerate(),
            source.getnchannels(),
            source.getsampwidth() * 8,
            source.getnframes(),
        )
    expected = (
        config.sample_rate,
        config.channels,
        config.sample_width_bits,
        config.sample_rate * duration_sec,
    )
    if actual != expected:
        raise ValueError(f"Generated WAV format {actual} does not match {expected}")


def _validate_pair(probe: dict, duration_sec: int) -> dict:
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    duration = float(probe["format"]["duration"])
    if abs(duration - duration_sec) > 0.05:
        raise ValueError(f"Pair duration {duration:.3f} does not match {duration_sec}")
    if (video.get("width"), video.get("height")) != (1080, 1920):
        raise ValueError("Pair is not 1080x1920")
    if video.get("avg_frame_rate") != "24/1":
        raise ValueError("Pair is not 24 fps")
    if int(audio.get("sample_rate", 0)) != 48000 or int(audio.get("channels", 0)) != 2:
        raise ValueError("Pair audio is not 48 kHz stereo")
    return {
        "durationSec": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frameRate": video["avg_frame_rate"],
        "videoCodec": video["codec_name"],
        "audioCodec": audio["codec_name"],
        "audioSampleRate": int(audio["sample_rate"]),
        "audioChannels": int(audio["channels"]),
    }


def render_round(
    *,
    db_path: Path,
    visual_id: str,
    config_path: Path,
    asset_root: Path,
    recipe_id: str,
    output_root: Path,
    count: int,
    ffmpeg: str,
    ffprobe: str,
    reuse_existing: bool,
) -> dict:
    initialize_registry(db_path)
    config = load_config(config_path, asset_root=asset_root)
    if recipe_id not in config.recipes:
        raise ValueError(f"Unknown audio recipe: {recipe_id}")
    recipe = config.recipes[recipe_id]
    visual = next(
        (item for item in list_visual_candidates_for_review(db_path) if item["visual_id"] == visual_id),
        None,
    )
    if visual is None:
        raise ValueError(f"Unknown visual candidate: {visual_id}")
    if float(visual["duration_sec"]) != recipe.duration_sec:
        raise ValueError(
            f"Visual is {visual['duration_sec']} seconds but {recipe_id} is {recipe.duration_sec}"
        )
    visual_path = Path(visual["media_path"])
    if not visual_path.is_file():
        raise FileNotFoundError(visual_path)

    output_root.mkdir(parents=True, exist_ok=True)
    audio_root = output_root / "audio"
    pair_root = output_root / "pairs"
    audio_root.mkdir(exist_ok=True)
    pair_root.mkdir(exist_ok=True)
    base_seed = _seed_base(EXPERIMENT_ID, visual_id, recipe_id)
    seeds = distinct_seeds(config, recipe_id, count, base_seed)
    rendered = []
    for index, seed in enumerate(seeds, start=1):
        audio_id = _stable_id("AUD", recipe_id, seed, config.generator_version)
        pair_id = _stable_id("PAIR", visual_id, audio_id)
        audio_path = audio_root / f"{audio_id}.wav"
        audio_manifest_path = audio_root / f"{audio_id}.json"
        pair_path = pair_root / f"{pair_id}.mp4"
        pair_manifest_path = pair_root / f"{pair_id}.json"

        if reuse_existing and audio_path.is_file() and audio_manifest_path.is_file():
            audio_manifest = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
        else:
            track = generate(config, recipe_id, seed, audio_path)
            _validate_wav(audio_path, config, recipe.duration_sec)
            bed = _asset(config, track.bed_id)
            gesture = _asset(config, track.gesture_id)
            audio_manifest = {
                "schemaVersion": "1.0",
                "candidateType": "audio",
                "audioId": audio_id,
                "experimentId": EXPERIMENT_ID,
                "recipe": {"id": recipe_id, "name": recipe.name},
                "durationSec": recipe.duration_sec,
                "seed": seed,
                "generatorVersion": config.generator_version,
                "ingredients": {
                    "bed": {
                        "id": bed.asset_id,
                        "name": bed.name,
                        "family": bed.family,
                        "source": bed.source,
                    },
                    "gesture": {
                        "id": gesture.asset_id,
                        "name": gesture.name,
                        "family": gesture.family,
                        "source": gesture.source,
                        "startSec": round(track.gesture_start_sec, 6),
                    },
                    "music": None,
                },
                "format": {
                    "container": "WAV",
                    "sampleRate": config.sample_rate,
                    "channels": config.channels,
                    "sampleWidthBits": config.sample_width_bits,
                    "nativeDuration": True,
                },
                "initialDisposition": "banked",
                "config": {
                    "path": str(config_path.resolve()),
                    "sha256": _sha256(config_path),
                    "privateAssetRoot": str(asset_root.resolve()),
                },
                "output": {"path": str(audio_path.resolve()), "sha256": _sha256(audio_path)},
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            audio_manifest_path.write_text(
                json.dumps(audio_manifest, indent=2) + "\n", encoding="utf-8"
            )
        register_audio_candidate(
            db_path,
            audio_id=audio_id,
            recipe_id=recipe_id,
            duration_sec=recipe.duration_sec,
            seed=seed,
            generator_version=config.generator_version,
            media_path=audio_path,
            manifest_path=audio_manifest_path,
            status="banked",
        )

        if not (reuse_existing and pair_path.is_file() and pair_manifest_path.is_file()):
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(visual_path),
                    "-i",
                    str(audio_path),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-t",
                    str(recipe.duration_sec),
                    "-movflags",
                    "+faststart",
                    str(pair_path),
                ],
                check=True,
                capture_output=True,
            )
            technical = _validate_pair(_probe(ffprobe, pair_path), recipe.duration_sec)
            pair_manifest = {
                "schemaVersion": "1.0",
                "candidateType": "visual_audio_pair",
                "pairId": pair_id,
                "experimentId": EXPERIMENT_ID,
                "optionNumber": index,
                "portraitId": visual["portrait_id"],
                "portraitRevisionId": visual["revision_id"],
                "visual": {
                    "id": visual_id,
                    "path": str(visual_path.resolve()),
                    "sha256": _sha256(visual_path),
                    "policy": "Locked selected visual; video stream copied without re-encoding",
                },
                "audio": {
                    "id": audio_id,
                    "path": str(audio_path.resolve()),
                    "sha256": _sha256(audio_path),
                    "recipeId": recipe_id,
                    "nativeDuration": True,
                },
                "durationSec": recipe.duration_sec,
                "filmGrain": "none",
                "bankPolicy": {
                    "unusedAudio": "banked automatically",
                    "selectedAudio": "retired from future final use",
                    "rejectedPairAudio": "banked unless explicitly retired",
                },
                "technicalValidation": technical,
                "output": {"path": str(pair_path.resolve()), "sha256": _sha256(pair_path)},
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            pair_manifest_path.write_text(
                json.dumps(pair_manifest, indent=2) + "\n", encoding="utf-8"
            )
        else:
            pair_manifest = json.loads(pair_manifest_path.read_text(encoding="utf-8"))
            technical = pair_manifest["technicalValidation"]

        register_pair_candidate(
            db_path,
            pair_id=pair_id,
            experiment_id=EXPERIMENT_ID,
            portrait_id=visual["portrait_id"],
            visual_id=visual_id,
            audio_id=audio_id,
            media_path=pair_path,
            manifest_path=pair_manifest_path,
            status="ready_for_review",
        )
        rendered.append(
            {
                "optionNumber": index,
                "pairId": pair_id,
                "audioId": audio_id,
                "seed": seed,
                "bedId": audio_manifest["ingredients"]["bed"]["id"],
                "gestureId": audio_manifest["ingredients"]["gesture"]["id"],
                "pair": str(pair_path.resolve()),
                "manifest": str(pair_manifest_path.resolve()),
                "technicalValidation": technical,
            }
        )

    summary = {
        "schemaVersion": "1.0",
        "experimentId": EXPERIMENT_ID,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "portraitId": visual["portrait_id"],
        "portraitRevisionId": visual["revision_id"],
        "visualId": visual_id,
        "audioRecipe": {"id": recipe_id, "name": recipe.name},
        "durationSec": recipe.duration_sec,
        "nativeDuration": True,
        "candidateCount": len(rendered),
        "audioBankPolicy": "Unused audio remains available automatically; no bank toggle is required.",
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
    parser.add_argument("--visual-id", default=DEFAULT_VISUAL_ID)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "components/audio-generator/config/generator.xml",
    )
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--recipe", default=DEFAULT_RECIPE_ID)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "workspace/pairing-nychildren-v27",
    )
    parser.add_argument("--count", type=int, choices=range(1, 33), default=10)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    summary = render_round(
        db_path=args.db,
        visual_id=args.visual_id,
        config_path=args.config,
        asset_root=args.asset_root,
        recipe_id=args.recipe,
        output_root=args.output_root,
        count=args.count,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
        reuse_existing=args.reuse_existing,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
