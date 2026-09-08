#!/usr/bin/env python3
"""Prepare a private application review from exact, independently approved media.

This AV Assembler entry point never generates media components or writes reviews.
It leaves historical pair records untouched, including superseded experiments.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/assemble_pair_round"))
sys.path.insert(0, str(ROOT / "tools/verify_production"))
from hpr_component_paths import component_root, load_component_lock
from assemble_pair_round import _sha256, _probe, _measure_loudness, _validate_pair, _validate_source_wav
from verify_production import verify_approved_visuals, verify_no_embedded_generators


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_file(path, expected=None):
    path = Path(path)
    require(path.is_file(), f"Missing file: {path}")
    actual = _sha256(path)
    require(expected is None or actual == expected, f"Fingerprint changed: {path}")
    return {"path": str(path.resolve()), "sha256": actual}


def latest_review(db, kind, identity):
    row = db.execute(
        "SELECT * FROM candidate_reviews WHERE subject_kind=? AND subject_id=? ORDER BY review_id DESC LIMIT 1",
        (kind, identity),
    ).fetchone()
    return dict(row) if row else None


def require_approval(review, identity):
    require(review is not None and review["selected"] == 1 and review["rejected"] == 0,
            f"Current explicit human approval required: {identity}")


def check_audio(db, identity):
    row = db.execute("SELECT * FROM audio_candidates WHERE audio_id=?", (identity,)).fetchone()
    require(row is not None, f"Unknown audio: {identity}")
    review = latest_review(db, "audio", identity)
    require_approval(review, identity)
    require(row["status"] == "banked", f"Audio is unavailable: {identity}")
    require(row["duration_sec"] == 11, f"Native eleven-second audio required: {identity}")
    manifest = json.loads(Path(row["manifest_path"]).read_text())
    require(manifest["audioId"] == identity, f"Audio manifest identity mismatch: {identity}")
    require(manifest.get("format", {}).get("nativeDuration") is True and
            manifest.get("durationSec") == 11 and
            manifest.get("designLineage", {}).get("nativeDurationSec") == 11 and
            manifest.get("loopNativeStructure", {}).get("extendedFromShorterTrack") is False,
            f"Native-duration provenance required: {identity}")
    require(manifest.get("loopValidation", {}).get("click_check_passed") is True,
            f"Audio loop screening failed: {identity}")
    media = checked_file(row["media_path"], manifest["output"]["sha256"])
    audio_format = _validate_source_wav(Path(media["path"]), 11)
    level = _measure_loudness("ffmpeg", Path(media["path"]))
    require(abs(level["integratedLufs"] + 22) <= .2, f"Audio delivery level changed: {identity}")
    require(level["truePeakDbfs"] <= -1, f"Audio true peak exceeds delivery ceiling: {identity}")
    return {"id": identity, "media": media, "manifest": checked_file(row["manifest_path"]),
            "humanApproval": review, "format": audio_format, "loudness": level,
            "provenance": manifest}


def video_packets(path):
    return subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-c:v", "copy", "-f", "hash", "-hash", "sha256", "-"
    ], text=True).strip()


def decoded_loop(path):
    data = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), "-vf",
        "select='eq(n,0)+eq(n,1)+eq(n,262)+eq(n,263)'", "-fps_mode", "passthrough",
        "-pix_fmt", "gray", "-f", "rawvideo", "-"
    ])
    size = 1080 * 1920
    require(len(data) == size * 4, f"Cannot inspect video endpoints: {path}")
    frames = [data[i*size:(i+1)*size] for i in range(4)]
    def difference(left, right):
        counts = Counter(abs(a-b) for a,b in zip(left,right))
        return {"meanLumaCodes": sum(k*n for k,n in counts.items())/size,
                "maxLumaCodes": max(counts)}
    return {"endToStart": difference(frames[3], frames[0]),
            "startAdjacent": difference(frames[0],frames[1]),
            "endAdjacent": difference(frames[2],frames[3]),
            "interpretation": "Approved source states match; lossy H.264 endpoint pixels can differ. Final human loop review remains required."}


def check_visual(db, baseline):
    identity = baseline["visualId"]
    row = db.execute("SELECT * FROM visual_candidates WHERE visual_id=?", (identity,)).fetchone()
    require(row is not None, f"Missing registered visual: {identity}")
    review = latest_review(db, "visual", identity)
    require_approval(review, identity)
    require(review["rating"] == 5, f"Five-star production visual required: {identity}")
    media = checked_file(ROOT / baseline["mediaPath"], baseline["mediaSha256"])
    require(Path(row["media_path"]).resolve() == Path(media["path"]), "Registered visual path differs from baseline")
    manifest_file = checked_file(ROOT / baseline["manifestPath"], baseline["manifestSha256"])
    manifest = json.loads(Path(manifest_file["path"]).read_text())
    probe = _probe("ffprobe", Path(media["path"]))
    require(len(probe["streams"]) == 1, "Production visual must be silent")
    stream = probe["streams"][0]
    require(stream["codec_type"] == "video" and stream["codec_name"] == "h264" and
            (stream["width"],stream["height"],stream["avg_frame_rate"],stream["nb_frames"]) == (1080,1920,"24/1","264") and
            float(stream["duration"]) == 11 and float(stream["start_time"]) == 0,
            "Production visual format changed")
    require(all(stream[k] == "bt709" for k in ["color_space","color_transfer","color_primaries"])
            and stream["color_range"] == "tv", "Production color metadata changed")
    require(manifest["geometry"]["fixed"] and manifest["loopSafe"] and manifest["field"]["firstLastMaskIdentical"],
            "Fixed, loop-safe visual required")
    require(manifest.get("grain", "none") == "none" and manifest.get("grainTreatment", {"mode":"none"})["mode"] == "none",
            "Film grain is forbidden")
    if baseline["project"] == "Infinity":
        require(manifest["backgroundRecipeId"] == "IBN-001" and manifest["backgroundSpeed"] == 0 and
                manifest["backgroundParameters"]["numberMotion"] == "static", "Approved static Infinity field required")
    dependencies = []
    artifacts = manifest["sourceArtifacts"]
    for key in ["normalizedFinal","underResolvedSurrogate","layeredTiff","subjectLayer","backgroundLayer"]:
        if key in artifacts:
            dependencies.append(checked_file(artifacts[key], artifacts[key+"Sha256"]))
    if "portrait" in manifest:
        dependencies.append(checked_file(manifest["portrait"],manifest["portraitSha256"]))
    if "backgroundTypography" in manifest:
        typography = manifest["backgroundTypography"]
        dependencies.append(checked_file(typography["localFile"], typography["localFileSha256"]))
        dependencies.append(checked_file(manifest["intermediateBackground"],manifest["intermediateBackgroundSha256"]))
    return {"project": baseline["project"], "id": identity, "portraitId": row["portrait_id"],
            "revisionId": row["revision_id"], "media": media, "manifest": manifest_file,
            "humanApproval": review, "dependencies": dependencies, "provenance": manifest,
            "videoPacketHash": video_packets(media["path"]), "decodedLoop": decoded_loop(media["path"])}


def assemble(visual, audio, output):
    require(not output.exists(), f"Refusing to overwrite: {output}")
    checked_file(visual["media"]["path"], visual["media"]["sha256"])
    checked_file(audio["media"]["path"], audio["media"]["sha256"])
    subprocess.run([
        "ffmpeg", "-v", "error", "-n", "-i", visual["media"]["path"],
        "-i", audio["media"]["path"], "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-t", "11",
        "-movflags", "+faststart", str(output)
    ], check=True)
    probe = _probe("ffprobe", output)
    technical = _validate_pair(probe, 11)
    require(len(probe["streams"]) == 2, "Exactly one video and one audio stream required")
    for stream in probe["streams"]:
        require(abs(float(stream["start_time"])) < 1/48000 and
                abs(float(stream["duration"])-11) < 1/48000, "AV timing mismatch")
    require(video_packets(output) == visual["videoPacketHash"], "Encoded video changed during assembly")
    level = _measure_loudness("ffmpeg", output)
    require(abs(level["integratedLufs"] - audio["loudness"]["integratedLufs"]) <= .2, "AAC changed loudness")
    require(level["truePeakDbfs"] <= -1, "AAC true peak exceeds ceiling")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(output),"-f","null","-"], check=True)
    checked_file(visual["media"]["path"], visual["media"]["sha256"])
    checked_file(audio["media"]["path"], audio["media"]["sha256"])
    return {"media": checked_file(output), "technical": technical, "aacLoudness": level,
            "videoStreamCopiedAndVerified": True, "audioFiltersApplied": False,
            "audioGainChangeDb": 0, "humanAVApproval": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "workspace/registry/hpr.sqlite3")
    parser.add_argument("--audio-id", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(len(args.audio_id) == 10 and len(set(args.audio_id)) == 10, "Supply ten explicit, unique audio IDs")
    require(not args.output.exists(), "Use a new output folder; prior review artifacts are immutable")
    verify_no_embedded_generators()
    lock = load_component_lock()
    for name in lock["components"]:
        component_root(name)
    verify_approved_visuals()
    db = sqlite3.connect(args.db.resolve().as_uri()+"?mode=ro",uri=True)
    db.row_factory = sqlite3.Row
    require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Registry integrity check failed")
    baseline = json.loads((ROOT / "config/approved-visual-baseline.json").read_text())
    visuals = [check_visual(db, v) for v in baseline["visuals"]]
    audio = [check_audio(db, identity) for identity in args.audio_id]
    db.close()
    args.output.mkdir(parents=True)
    report = {"schemaVersion":"1.0", "purpose":"Radcliffe Yard application AV review",
              "createdAt":datetime.now(timezone.utc).isoformat(), "status":"awaiting_human_pair_selection",
              "componentLock":lock, "umbrellaCommit":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),
              "assembler":checked_file(__file__), "assemblyHelpers":checked_file(ROOT / "tools/assemble_pair_round/assemble_pair_round.py"),
              "registry":checked_file(args.db), "visuals":visuals, "audio":audio, "pairs":[]}
    for visual in visuals:
        folder = args.output / visual["project"]
        folder.mkdir()
        for index, track in enumerate(audio,1):
            destination = folder / f"option-{index:02d}.mp4"
            result = assemble(visual,track,destination)
            result.update({"project":visual["project"],"option":index,"visualId":visual["id"],"audioId":track["id"],
                           "audioApprovalReviewId":track["humanApproval"]["review_id"],
                           "relativePath":destination.relative_to(args.output).as_posix()})
            destination.with_suffix(".json").write_text(json.dumps(result,indent=2)+"\n")
            report["pairs"].append(result)
            print(f"Verified {visual['project']} option {index:02d}",flush=True)
    (args.output / "provenance.json").write_text(json.dumps(report,indent=2)+"\n")
    (args.output / "review-data.js").write_text("window.HPR_REVIEW="+json.dumps({
        "audio":[{"option":i,"id":a["id"],"rating":a["humanApproval"]["rating"]} for i,a in enumerate(audio,1)],
        "pairs":[{k:p[k] for k in ["project","option","audioId","relativePath"]} for p in report["pairs"]]
    })+";\n")
    shutil.copyfile(Path(__file__).with_name("review.html"),args.output / "index.html")
    print(f"Review ready: {args.output / 'index.html'}")


if __name__ == "__main__":
    main()
