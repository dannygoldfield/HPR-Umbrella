#!/usr/bin/env python3
"""Assemble one locked visual with an explicit rolling pool of audio candidates."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import wave


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "components/registry/src"))

from hpr_registry import (  # noqa: E402
    initialize_registry,
    list_audio_candidates_for_review,
    list_visual_candidates_for_review,
    register_pair_candidate,
    supersede_pair_experiment,
)


LOUDNESS_RE = re.compile(r"I:\s+(-?\d+(?:\.\d+)?) LUFS")
TRUE_PEAK_RE = re.compile(r"Peak:\s+(-?\d+(?:\.\d+)?) dBFS")
# Human approval is the gate between audio review and AV assembly. Automated
# delivery checks may register a candidate as ready_for_review, but that status
# must never make the candidate eligible for pairing.
ELIGIBLE_AUDIO_STATUSES = {"banked"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\0".join(map(str, parts)).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12].upper()}"


def _probe(ffprobe: str, path: Path) -> dict[str, object]:
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _measure_loudness(ffmpeg: str, path: Path) -> dict[str, float]:
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    output = completed.stderr + completed.stdout
    loudness = LOUDNESS_RE.findall(output)
    true_peak = TRUE_PEAK_RE.findall(output)
    if completed.returncode or not loudness or not true_peak:
        raise RuntimeError(f"Could not measure loudness for {path}")
    return {"integratedLufs": float(loudness[-1]), "truePeakDbfs": float(true_peak[-1])}


def _validate_source_wav(path: Path, duration_sec: int) -> dict[str, int]:
    with wave.open(str(path), "rb") as source:
        result = {
            "sampleRate": source.getframerate(),
            "channels": source.getnchannels(),
            "sampleWidthBits": source.getsampwidth() * 8,
            "frameCount": source.getnframes(),
        }
    expected_frames = result["sampleRate"] * duration_sec
    if result != {
        "sampleRate": 48000,
        "channels": 2,
        "sampleWidthBits": 16,
        "frameCount": expected_frames,
    }:
        raise ValueError(f"Unexpected source WAV format for {path}: {result}")
    return result


def _validate_pair(probe: dict[str, object], duration_sec: int) -> dict[str, object]:
    streams = probe["streams"]
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    audio = next(stream for stream in streams if stream["codec_type"] == "audio")
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


def assemble_round(
    *,
    experiment_id: str,
    db_path: Path,
    visual_id: str,
    audio_ids: list[str],
    output_root: Path,
    ffmpeg: str,
    ffprobe: str,
    reuse_existing: bool,
    supersede_experiments: list[str],
) -> dict[str, object]:
    if len(audio_ids) != 10 or len(set(audio_ids)) != 10:
        raise ValueError("A rolling pair round requires exactly ten unique audio IDs")
    initialize_registry(db_path)
    visual = next(
        (item for item in list_visual_candidates_for_review(db_path) if item["visual_id"] == visual_id),
        None,
    )
    if visual is None:
        raise ValueError(f"Unknown visual candidate: {visual_id}")
    if not visual["selected"]:
        raise ValueError(f"Visual candidate is not the selected visual: {visual_id}")
    duration_sec = int(float(visual["duration_sec"]))
    if duration_sec != 11:
        raise ValueError("The current rolling pool requires an 11-second visual")
    visual_path = Path(visual["media_path"])
    if not visual_path.is_file():
        raise FileNotFoundError(visual_path)

    audio_by_id = {item["audio_id"]: item for item in list_audio_candidates_for_review(db_path)}
    missing = [audio_id for audio_id in audio_ids if audio_id not in audio_by_id]
    if missing:
        raise ValueError(f"Unknown audio IDs: {', '.join(missing)}")

    output_root.mkdir(parents=True, exist_ok=True)
    pair_root = output_root / "pairs"
    pair_root.mkdir(exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    candidates: list[dict[str, object]] = []
    for position, audio_id in enumerate(audio_ids, start=1):
        audio = audio_by_id[audio_id]
        if audio["render_status"] not in ELIGIBLE_AUDIO_STATUSES:
            raise ValueError(f"Audio is not eligible for pairing: {audio_id} ({audio['render_status']})")
        if audio["rejected"]:
            raise ValueError(f"Rejected audio cannot be paired: {audio_id}")
        if abs(float(audio["duration_sec"]) - duration_sec) > 0.001:
            raise ValueError(f"Audio duration does not match the visual: {audio_id}")
        audio_path = Path(audio["media_path"])
        audio_manifest_path = Path(audio["manifest_path"])
        if not audio_path.is_file() or not audio_manifest_path.is_file():
            raise FileNotFoundError(audio_path if not audio_path.is_file() else audio_manifest_path)
        audio_manifest = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
        if _sha256(audio_path) != audio_manifest["output"]["sha256"]:
            raise ValueError(f"Audio fingerprint mismatch: {audio_id}")
        source_format = _validate_source_wav(audio_path, duration_sec)

        pair_id = _stable_id("PAIR", visual_id, audio_id)
        pair_path = pair_root / f"{pair_id}.mp4"
        pair_manifest_path = pair_root / f"{pair_id}.json"
        if not (reuse_existing and pair_path.is_file() and pair_manifest_path.is_file()):
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
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
                    "320k",
                    "-t",
                    str(duration_sec),
                    "-movflags",
                    "+faststart",
                    str(pair_path),
                ],
                check=True,
            )
            technical = _validate_pair(_probe(ffprobe, pair_path), duration_sec)
            source_loudness = _measure_loudness(ffmpeg, audio_path)
            pair_loudness = _measure_loudness(ffmpeg, pair_path)
            loudness_delta = round(
                pair_loudness["integratedLufs"] - source_loudness["integratedLufs"], 3
            )
            if abs(loudness_delta) > 0.2:
                raise ValueError(f"Pairing changed audio loudness by {loudness_delta} dB")
            pair_manifest = {
                "schemaVersion": "1.0",
                "candidateType": "visual_audio_pair",
                "pairId": pair_id,
                "experimentId": experiment_id,
                "optionNumber": position,
                "portraitId": visual["portrait_id"],
                "portraitRevisionId": visual["revision_id"],
                "visual": {
                    "id": visual_id,
                    "path": str(visual_path.resolve()),
                    "sha256": _sha256(visual_path),
                    "policy": "locked selected visual; video stream copied without re-encoding",
                },
                "audio": {
                    "id": audio_id,
                    "path": str(audio_path.resolve()),
                    "sha256": _sha256(audio_path),
                    "manifestPath": str(audio_manifest_path.resolve()),
                    "recipeId": audio["recipe_id"],
                    "sourceDisposition": audio["render_status"],
                    "nativeDuration": True,
                    "mixing": "none",
                    "gainChangeDb": 0.0,
                },
                "durationSec": duration_sec,
                "reviewActions": {
                    "selectPair": "assign audio to this portrait",
                    "bankAudio": "reject this pairing while keeping audio reusable",
                    "rejectAudio": "reject this pairing and retire the audio mix",
                },
                "technicalValidation": {
                    **technical,
                    "sourceWav": source_format,
                    "sourceLoudness": source_loudness,
                    "pairLoudness": pair_loudness,
                    "loudnessDeltaDb": loudness_delta,
                    "sourceLoopValidation": audio_manifest.get("loopValidation"),
                    "videoStreamCopied": True,
                    "audioFiltersApplied": False,
                },
                "output": {"path": str(pair_path.resolve()), "sha256": _sha256(pair_path)},
                "createdAt": created_at,
            }
            pair_manifest_path.write_text(
                json.dumps(pair_manifest, indent=2) + "\n", encoding="utf-8"
            )
        else:
            pair_manifest = json.loads(pair_manifest_path.read_text(encoding="utf-8"))

        register_pair_candidate(
            db_path,
            pair_id=pair_id,
            experiment_id=experiment_id,
            portrait_id=visual["portrait_id"],
            visual_id=visual_id,
            audio_id=audio_id,
            media_path=pair_path,
            manifest_path=pair_manifest_path,
            status="ready_for_review",
        )
        candidates.append(
            {
                "optionNumber": position,
                "pairId": pair_id,
                "audioId": audio_id,
                "audioSourceDisposition": audio["render_status"],
                "pair": str(pair_path.resolve()),
                "manifest": str(pair_manifest_path.resolve()),
            }
        )

    superseded = []
    for old_experiment in supersede_experiments:
        superseded.append(
            {
                "experimentId": old_experiment,
                "candidateCount": supersede_pair_experiment(
                    db_path, old_experiment, supersede_audio=False
                ),
            }
        )
    summary = {
        "schemaVersion": "1.0",
        "experimentId": experiment_id,
        "createdAt": created_at,
        "portraitId": visual["portrait_id"],
        "visualId": visual_id,
        "durationSec": duration_sec,
        "candidateCount": len(candidates),
        "rollingPoolSize": 10,
        "assemblyPolicy": "exact registered audio plus exact locked visual; no generation or mixing",
        "supersededExperiments": superseded,
        "candidates": candidates,
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
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--visual-id", required=True)
    parser.add_argument("--audio-id", action="append", required=True, dest="audio_ids")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument(
        "--supersede-experiment",
        action="append",
        default=[],
        dest="supersede_experiments",
    )
    args = parser.parse_args()
    result = assemble_round(
        experiment_id=args.experiment_id,
        db_path=args.db,
        visual_id=args.visual_id,
        audio_ids=args.audio_ids,
        output_root=args.output_root,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
        reuse_existing=args.reuse_existing,
        supersede_experiments=args.supersede_experiments,
    )
    print(
        f"Assembled {result['candidateCount']} exact audio/visual pairs for "
        f"{result['visualId']}"
    )


if __name__ == "__main__":
    main()
