from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess


SUPPORTED_DURATIONS = {7, 9, 11}


@dataclass(frozen=True)
class CandidatePlan:
    candidate_id: str
    portrait: Path
    grain: Path
    duration_sec: int
    seed: int
    video_preset: str
    audio_recipe: str
    silent_video: Path
    soundtrack: Path
    final_video: Path
    manifest: Path


@dataclass(frozen=True)
class CandidateResult:
    plan: CandidatePlan
    video_generator_version: str
    audio_generator_version: str
    audio_bed_id: str
    audio_gesture_id: str
    audio_music_stem_id: str | None


def find_ffmpeg() -> str:
    """Locate FFmpeg without importing either media generator."""
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("FFmpeg is required for AV assembly") from exc


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return normalized or "portrait"


def build_plan(
    portrait: Path,
    grain: Path,
    duration_sec: int,
    seed: int,
    video_preset: str,
    audio_recipe: str,
    output_root: Path,
) -> CandidatePlan:
    if duration_sec not in SUPPORTED_DURATIONS:
        raise ValueError(f"Unsupported duration: {duration_sec}")
    candidate_id = (
        f"HPR-{_safe_name(portrait.stem)}-{duration_sec}s-"
        f"{video_preset}-{audio_recipe}-seed-{seed}"
    )
    work = output_root / "work" / candidate_id
    final = output_root / "candidates" / f"{candidate_id}.mp4"
    return CandidatePlan(
        candidate_id=candidate_id,
        portrait=portrait,
        grain=grain,
        duration_sec=duration_sec,
        seed=seed,
        video_preset=video_preset,
        audio_recipe=audio_recipe,
        silent_video=work / "silent.mp4",
        soundtrack=work / "soundtrack.wav",
        final_video=final,
        manifest=final.with_suffix(".json"),
    )


def mux(video: Path, audio: Path, output: Path, ffmpeg: str | None = None) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg or find_ffmpeg(),
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
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
        "-shortest",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)
    return output


def generate_candidate(
    plan: CandidatePlan,
    video_config_path: Path,
    audio_config_path: Path,
) -> CandidateResult:
    # This legacy convenience path intentionally imports the canonical,
    # separately installed generator packages only when invoked. Production
    # pairing normally consumes already-reviewed silent video and audio files.
    from hpr_audio_generator.config import load_config as load_audio_config
    from hpr_audio_generator.generator import generate as generate_audio
    from hpr_video_generator.config import load_config as load_video_config
    from hpr_video_generator.generator import Candidate as VideoCandidate
    from hpr_video_generator.generator import generate as generate_video

    video_config = load_video_config(video_config_path)
    if plan.video_preset not in video_config.presets:
        raise ValueError(f"Unknown video preset: {plan.video_preset}")

    audio_config = load_audio_config(audio_config_path)
    if plan.audio_recipe not in audio_config.recipes:
        raise ValueError(f"Unknown audio recipe: {plan.audio_recipe}")
    audio_recipe = audio_config.recipes[plan.audio_recipe]
    if audio_recipe.duration_sec != plan.duration_sec:
        raise ValueError(
            f"Duration mismatch: candidate is {plan.duration_sec}s but "
            f"{plan.audio_recipe} is {audio_recipe.duration_sec}s"
        )

    plan.silent_video.parent.mkdir(parents=True, exist_ok=True)
    video_candidate = VideoCandidate(
        portrait=plan.portrait,
        grain=plan.grain,
        preset=video_config.presets[plan.video_preset],
        seed=plan.seed,
        duration_sec=plan.duration_sec,
        output=plan.silent_video,
    )
    generate_video(video_config, video_candidate)
    audio_track = generate_audio(
        audio_config,
        plan.audio_recipe,
        plan.seed,
        plan.soundtrack,
    )
    mux(plan.silent_video, plan.soundtrack, plan.final_video)

    result = CandidateResult(
        plan=plan,
        video_generator_version=video_config.version,
        audio_generator_version=audio_config.generator_version,
        audio_bed_id=audio_track.bed_id,
        audio_gesture_id=audio_track.gesture_id,
        audio_music_stem_id=audio_track.music_stem_id,
    )
    manifest = asdict(result)
    manifest["plan"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in manifest["plan"].items()
    }
    plan.manifest.parent.mkdir(parents=True, exist_ok=True)
    plan.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    return result
