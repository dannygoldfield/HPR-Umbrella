"""Apply locally managed scanned-film grain to an approved HPR visual.

The grain stage is deliberately downstream of portrait development and Infinity
background compositing.  It changes luma only, never geometry or color, and it
keeps the original scan plates outside the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .generator import find_ffmpeg


@dataclass(frozen=True)
class FilmGrainPlate:
    id: str
    filename: str
    film_format: str
    source_strength: str


@dataclass(frozen=True)
class FilmGrainRecipe:
    id: str
    name: str
    plate_id: str | None
    opacity: float


@dataclass(frozen=True)
class FilmGrainConfig:
    version: str
    experiment_id: str
    purpose: str
    source: dict[str, str]
    base_visuals: tuple[dict[str, str], ...]
    plates: dict[str, FilmGrainPlate]
    recipes: tuple[FilmGrainRecipe, ...]


@dataclass(frozen=True)
class FilmGrainCandidate:
    portrait_id: str
    revision_id: str
    parent_visual_id: str
    parent_visual: Path
    recipe: FilmGrainRecipe
    plate: FilmGrainPlate | None
    plate_path: Path | None
    candidate_seed: int
    sample_seed: int
    duration_sec: int
    output: Path


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def load_film_grain_config(path: Path) -> FilmGrainConfig:
    raw = _object(json.loads(path.read_text(encoding="utf-8")), "Film-grain config")
    plates: dict[str, FilmGrainPlate] = {}
    for plate_id, value in _object(raw.get("plates"), "plates").items():
        item = _object(value, f"plate {plate_id}")
        plates[plate_id] = FilmGrainPlate(
            id=plate_id,
            filename=str(item["filename"]),
            film_format=str(item["filmFormat"]),
            source_strength=str(item["sourceStrength"]),
        )

    recipes: list[FilmGrainRecipe] = []
    seen: set[str] = set()
    for value in raw.get("recipes", []):
        item = _object(value, "recipe")
        recipe_id = str(item["id"])
        if recipe_id in seen:
            raise ValueError(f"Duplicate film-grain recipe: {recipe_id}")
        seen.add(recipe_id)
        plate_id = item.get("plate")
        if plate_id is not None and plate_id not in plates:
            raise ValueError(f"Recipe {recipe_id} refers to unknown plate {plate_id}")
        opacity = float(item["opacity"])
        if not 0.0 <= opacity <= 1.0:
            raise ValueError(f"Recipe {recipe_id} opacity must be between 0 and 1")
        if plate_id is None and opacity != 0.0:
            raise ValueError(f"Control recipe {recipe_id} must have zero opacity")
        recipes.append(
            FilmGrainRecipe(
                id=recipe_id,
                name=str(item["name"]),
                plate_id=plate_id,
                opacity=opacity,
            )
        )
    if not recipes:
        raise ValueError("Film-grain config requires at least one recipe")

    base_visuals = raw.get("baseVisuals", [])
    if not isinstance(base_visuals, list) or not base_visuals:
        raise ValueError("Film-grain config requires baseVisuals")
    source = _object(raw.get("source"), "source")
    return FilmGrainConfig(
        version=str(raw["version"]),
        experiment_id=str(raw["experimentId"]),
        purpose=str(raw["purpose"]),
        source={str(key): str(value) for key, value in source.items()},
        base_visuals=tuple(_object(item, "base visual") for item in base_visuals),
        plates=plates,
        recipes=tuple(recipes),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_ffprobe(ffmpeg: str) -> str:
    direct = shutil.which("ffprobe")
    if direct:
        return direct
    sibling = Path(ffmpeg).with_name("ffprobe")
    if sibling.is_file():
        return str(sibling)
    raise RuntimeError("FFprobe is required to audit film-grain sources and outputs")


def _probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration,color_range,color_space,color_transfer,color_primaries",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout).get("streams", [])
    if len(streams) != 1:
        raise ValueError(f"Expected one primary video stream in {path}")
    return streams[0]


def sample_window(sample_seed: int, *, source_frames: int, output_frames: int) -> tuple[int, float]:
    available = source_frames - output_frames
    if available < 0:
        raise ValueError("The grain plate is shorter than the requested output")
    start_frame = sample_seed % (available + 1)
    crop_fraction = ((sample_seed >> 12) % 10001) / 10000.0
    return start_frame, crop_fraction


def build_filter(
    *,
    width: int,
    height: int,
    fps: int,
    frames: int,
    recipe: FilmGrainRecipe,
    start_frame: int = 0,
    crop_fraction: float = 0.5,
) -> str:
    if not 0.0 <= crop_fraction <= 1.0:
        raise ValueError("crop_fraction must be between 0 and 1")
    base = (
        f"[0:v]fps={fps},trim=end_frame={frames},setpts=PTS-STARTPTS,"
        f"scale={width}:{height}:flags=lanczos,setsar=1,format=yuv444p"
    )
    if recipe.plate_id is None:
        return (
            base
            + ",format=yuv420p,setparams=range=tv:color_primaries=bt709:"
            "color_trc=bt709:colorspace=bt709[out]"
        )

    base += ",extractplanes=y+u+v[base_y][base_u][base_v]"
    grain = (
        f"[1:v]trim=start_frame={start_frame}:end_frame={start_frame + frames},"
        f"setpts=PTS-STARTPTS,fps={fps},scale=-2:{height}:flags=lanczos,"
        f"format=gray,crop={width}:{height}:x='(iw-{width})*{crop_fraction:.4f}':y=0[grain_y]"
    )
    composite = (
        f"[base_y][grain_y]blend=all_mode=overlay:all_opacity={recipe.opacity:.4f}[textured_y];"
        f"[textured_y][base_u][base_v]mergeplanes=0x001020:yuv444p,format=yuv420p,"
        "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709[out]"
    )
    return ";".join((base, grain, composite))


def generate_film_grain_candidate(
    candidate: FilmGrainCandidate,
    *,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    if not candidate.parent_visual.is_file():
        raise FileNotFoundError(candidate.parent_visual)
    if candidate.recipe.plate_id is not None:
        if candidate.plate is None or candidate.plate_path is None:
            raise ValueError("A grained recipe requires a resolved plate")
        if not candidate.plate_path.is_file():
            raise FileNotFoundError(candidate.plate_path)

    ffmpeg_path = ffmpeg or find_ffmpeg()
    ffprobe = _find_ffprobe(ffmpeg_path)
    frames = candidate.duration_sec * fps
    parent_probe = _probe_video(candidate.parent_visual, ffprobe)
    if (
        int(parent_probe["width"]) != width
        or int(parent_probe["height"]) != height
        or parent_probe["r_frame_rate"] != f"{fps}/1"
        or int(parent_probe["nb_frames"]) != frames
    ):
        raise ValueError("The approved parent visual does not match the locked delivery specification")

    start_frame = 0
    crop_fraction = 0.5
    plate_probe: dict[str, Any] | None = None
    if candidate.plate_path is not None:
        plate_probe = _probe_video(candidate.plate_path, ffprobe)
        if plate_probe["r_frame_rate"] != f"{fps}/1":
            raise ValueError(f"Grain plate must be {fps} fps: {candidate.plate_path}")
        start_frame, crop_fraction = sample_window(
            candidate.sample_seed,
            source_frames=int(plate_probe["nb_frames"]),
            output_frames=frames,
        )

    candidate.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = ["-i", str(candidate.parent_visual)]
    if candidate.plate_path is not None:
        inputs.extend(["-i", str(candidate.plate_path)])
    filter_complex = build_filter(
        width=width,
        height=height,
        fps=fps,
        frames=frames,
        recipe=candidate.recipe,
        start_frame=start_frame,
        crop_fraction=crop_fraction,
    )
    command = [
        ffmpeg_path,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-movflags",
        "+faststart",
        str(candidate.output),
    ]
    subprocess.run(command, check=True)

    output_probe = _probe_video(candidate.output, ffprobe)
    if (
        int(output_probe["width"]) != width
        or int(output_probe["height"]) != height
        or output_probe["r_frame_rate"] != f"{fps}/1"
        or int(output_probe["nb_frames"]) != frames
        or output_probe.get("color_range") != "tv"
        or output_probe.get("color_space") != "bt709"
        or output_probe.get("color_transfer") != "bt709"
        or output_probe.get("color_primaries") != "bt709"
    ):
        raise RuntimeError(f"Rendered film-grain candidate failed delivery audit: {candidate.output}")

    manifest = {
        "schemaVersion": "1.0",
        "candidateType": "visual_film_grain_test",
        "portraitId": candidate.portrait_id,
        "portraitRevisionId": candidate.revision_id,
        "parentVisualId": candidate.parent_visual_id,
        "parentVisual": {
            "path": str(candidate.parent_visual.resolve()),
            "sha256": sha256(candidate.parent_visual),
            "unchangedAcrossRecipes": True,
        },
        "grainRecipeId": candidate.recipe.id,
        "grainRecipeName": candidate.recipe.name,
        "candidateSeed": candidate.candidate_seed,
        "sampleSeed": candidate.sample_seed,
        "durationSec": candidate.duration_sec,
        "fps": fps,
        "frameCount": frames,
        "width": width,
        "height": height,
        "colorTreatment": "luma-only; original chroma planes pass through unchanged",
        "geometryTreatment": "none",
        "grainTreatment": {
            "mode": "none" if candidate.plate is None else "scanned-plate-luma-overlay",
            "filmFormat": None if candidate.plate is None else candidate.plate.film_format,
            "sourceStrength": None if candidate.plate is None else candidate.plate.source_strength,
            "opacity": candidate.recipe.opacity,
            "startFrame": start_frame,
            "cropFraction": crop_fraction,
            "plateFilename": None if candidate.plate is None else candidate.plate.filename,
            "platePath": None if candidate.plate_path is None else str(candidate.plate_path.resolve()),
            "plateSha256": None if candidate.plate_path is None else sha256(candidate.plate_path),
            "loopBehavior": "random-frame continuity; boundary must be judged against ordinary adjacent grain changes",
        },
        "output": str(candidate.output.resolve()),
        "outputSha256": sha256(candidate.output),
        "outputProbe": output_probe,
        "ffmpegFilter": filter_complex,
        "ffmpegCommand": command,
    }
    candidate.output.with_suffix(".json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
