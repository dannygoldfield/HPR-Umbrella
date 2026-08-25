from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from hpr_registry import register_audio_candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_batch(db_path: Path, batch_manifest_path: Path) -> dict[str, object]:
    batch = json.loads(batch_manifest_path.read_text(encoding="utf-8"))
    if batch.get("candidateType") != "audio_review_batch":
        raise ValueError("Manifest is not an audio-only review batch")
    if not batch.get("requirements", {}).get("audioOnlyReview"):
        raise ValueError("Batch is not marked for independent audio review")
    registered: list[str] = []
    for item in batch["candidates"]:
        manifest_path = Path(item["manifest"]).resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        audio_id = item["audioId"]
        if manifest.get("audioId") != audio_id:
            raise ValueError(f"Candidate identity mismatch: {audio_id}")
        if manifest.get("batchId") != batch["batchId"]:
            raise ValueError(f"Candidate belongs to another batch: {audio_id}")
        if manifest.get("candidateType") != "audio":
            raise ValueError(f"Candidate is not standalone audio: {audio_id}")
        media_path = Path(manifest["output"]["path"]).resolve()
        if not media_path.is_file():
            raise ValueError(f"Missing audio output: {media_path}")
        if _sha256(media_path) != manifest["output"]["sha256"]:
            raise ValueError(f"Audio fingerprint mismatch: {audio_id}")
        register_audio_candidate(
            db_path,
            audio_id=audio_id,
            recipe_id=manifest["recipeId"],
            duration_sec=float(manifest["durationSec"]),
            seed=int(manifest["seed"]),
            generator_version=manifest["generatorVersion"],
            media_path=media_path,
            manifest_path=manifest_path,
            status="ready_for_review",
        )
        registered.append(audio_id)
    return {
        "batchId": batch["batchId"],
        "registeredCount": len(registered),
        "audioIds": registered,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register a completed Audio Generator batch for audio-only review"
    )
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--batch-manifest", required=True, type=Path)
    args = parser.parse_args()
    result = register_batch(args.db, args.batch_manifest)
    print(
        f"Registered {result['registeredCount']} candidates from {result['batchId']}"
    )


if __name__ == "__main__":
    main()
