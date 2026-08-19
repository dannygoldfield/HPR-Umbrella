from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

from PIL import Image, ImageCms, ImageDraw, ImageFilter

from .color_pipeline import (
    srgb_profile_bytes,
    transform_rgb16,
    under_resolved_rgb16,
    write_rgb16_png,
)
from .config import Config
from .development import DevelopmentConfig, DevelopmentRecipe, development_mask_frames


EFFECTS = {
    "momentum_wake",
    "emulsion_bloom",
    "floating_print",
    "negative_space_aperture",
    "residual_gesture",
    "incomplete_geometry",
    "borrowed_color_field",
}


def _numpy():
    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - environment-specific
        raise RuntimeError("NumPy is required for Infinity background generation") from error
    return np


@dataclass(frozen=True)
class InfinityBackgroundRecipe:
    id: str
    name: str
    effect: str
    strength: float
    speed: float
    description: str


@dataclass(frozen=True)
class InfinityBackgroundConfig:
    version: str
    experiment_id: str
    working_width: int
    working_height: int
    base_portrait_treatment: dict[str, Any]
    principle: str
    recipes: dict[str, InfinityBackgroundRecipe]


@dataclass(frozen=True)
class LayeredWorkingSources:
    layered_tiff: Path
    subject_png: Path
    background_png: Path
    subject_finished: Path
    subject_under_resolved: Path
    background_srgb: Path
    background_pixels: Any
    subject_pixels: Any
    subject_alpha: Any
    provenance: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_infinity_background_config(path: Path) -> InfinityBackgroundConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    recipes: dict[str, InfinityBackgroundRecipe] = {}
    for item in payload["recipes"]:
        recipe = InfinityBackgroundRecipe(
            id=item["id"],
            name=item["name"],
            effect=item["effect"],
            strength=float(item["strength"]),
            speed=float(item["speed"]),
            description=item["description"],
        )
        if recipe.effect not in EFFECTS:
            raise ValueError(f"{recipe.id} has an unsupported effect: {recipe.effect}")
        if not 0 < recipe.strength <= 0.25:
            raise ValueError(f"{recipe.id} strength must be greater than 0 and at most 0.25")
        if recipe.speed <= 0:
            raise ValueError(f"{recipe.id} speed must be greater than zero")
        if recipe.id in recipes:
            raise ValueError(f"Duplicate Infinity background recipe: {recipe.id}")
        recipes[recipe.id] = recipe
    if len(recipes) != 7:
        raise ValueError("The Infinity background comparison requires exactly seven recipes")
    return InfinityBackgroundConfig(
        version=payload["version"],
        experiment_id=payload["experimentId"],
        working_width=int(payload["workingWidth"]),
        working_height=int(payload["workingHeight"]),
        base_portrait_treatment=payload["basePortraitTreatment"],
        principle=payload["principle"],
        recipes=recipes,
    )


def _profile_description(profile: bytes) -> str:
    return ImageCms.getProfileDescription(
        ImageCms.ImageCmsProfile(BytesIO(profile))
    ).strip()


def _decode_png_rgba16(
    path: Path,
    ffmpeg: str,
    fallback_profile: bytes | None = None,
) -> tuple[Any, Any, bytes, str]:
    np = _numpy()
    with Image.open(path) as image:
        if image.mode != "RGBA":
            raise ValueError(f"{path.name} must be RGBA; found {image.mode}")
        width, height = image.size
        profile = image.info.get("icc_profile") or fallback_profile
        if not profile:
            raise ValueError(f"{path.name} requires an embedded ICC profile")
        description = _profile_description(profile)
    raw = subprocess.check_output(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba64le",
            "pipe:1",
        ]
    )
    expected = width * height * 4 * 2
    if len(raw) != expected:
        raise RuntimeError(f"Decoded {len(raw)} subject bytes; expected {expected}")
    rgba = np.frombuffer(raw, dtype="<u2").reshape(height, width, 4).copy()
    return rgba[:, :, :3], rgba[:, :, 3], profile, description


def _decode_png_rgb16(
    path: Path,
    ffmpeg: str,
    fallback_profile: bytes | None = None,
) -> tuple[Any, bytes, str]:
    np = _numpy()
    with Image.open(path) as image:
        if image.mode != "RGB":
            raise ValueError(f"{path.name} must be RGB; found {image.mode}")
        width, height = image.size
        profile = image.info.get("icc_profile") or fallback_profile
        if not profile:
            raise ValueError(f"{path.name} requires an embedded ICC profile")
        description = _profile_description(profile)
    raw = subprocess.check_output(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb48le",
            "pipe:1",
        ]
    )
    expected = width * height * 3 * 2
    if len(raw) != expected:
        raise RuntimeError(f"Decoded {len(raw)} background bytes; expected {expected}")
    pixels = np.frombuffer(raw, dtype="<u2").reshape(height, width, 3).copy()
    return pixels, profile, description


def _scaled_rgb16(path: Path, width: int, height: int, ffmpeg: str) -> Any:
    np = _numpy()
    raw = subprocess.check_output(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb48le",
            "pipe:1",
        ]
    )
    expected = width * height * 3 * 2
    if len(raw) != expected:
        raise RuntimeError(f"Scaled RGB byte count was {len(raw)}; expected {expected}")
    return np.frombuffer(raw, dtype="<u2").reshape(height, width, 3).copy()


def _scaled_alpha16(path: Path, width: int, height: int, ffmpeg: str) -> Any:
    np = _numpy()
    raw = subprocess.check_output(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
            "format=rgba64le,alphaextract,format=gray16le",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray16le",
            "pipe:1",
        ]
    )
    expected = width * height * 2
    if len(raw) != expected:
        raise RuntimeError(f"Scaled alpha byte count was {len(raw)}; expected {expected}")
    return np.frombuffer(raw, dtype="<u2").reshape(height, width).copy()


def prepare_layered_working_sources(
    *,
    layered_tiff: Path,
    subject_png: Path,
    background_png: Path,
    output_root: Path,
    working_width: int,
    working_height: int,
    surrogate_settings: dict[str, Any],
    ffmpeg: str,
) -> LayeredWorkingSources:
    np = _numpy()
    output_root.mkdir(parents=True, exist_ok=True)
    with Image.open(layered_tiff) as layered_image:
        layered_profile = layered_image.info.get("icc_profile")
        if not layered_profile:
            raise ValueError(f"{layered_tiff.name} requires an embedded ICC profile")
        layered_profile_name = _profile_description(layered_profile)
    subject_rgb, subject_alpha, subject_profile, subject_profile_name = _decode_png_rgba16(
        subject_png, ffmpeg, layered_profile
    )
    background_rgb, background_profile, background_profile_name = _decode_png_rgb16(
        background_png, ffmpeg, layered_profile
    )
    if subject_rgb.shape[:2] != background_rgb.shape[:2]:
        raise ValueError("Subject and background layers must share dimensions")
    if subject_profile_name != background_profile_name:
        raise ValueError("Subject and background layers must share an ICC profile")
    if int(subject_alpha.min()) != 0 or int(subject_alpha.max()) != 65535:
        raise ValueError("Subject layer must contain both transparent and opaque pixels")

    working_profile = srgb_profile_bytes()
    subject_srgb = transform_rgb16(subject_rgb, subject_profile, working_profile)
    background_srgb_pixels = transform_rgb16(
        background_rgb, background_profile, working_profile
    )
    subject_under = under_resolved_rgb16(subject_srgb, surrogate_settings)

    subject_finished_path = output_root / "infinity-subject-finished-srgb-16bit.png"
    subject_under_path = output_root / "infinity-subject-under-resolved-srgb-16bit.png"
    background_srgb_path = output_root / "infinity-background-srgb-16bit.png"
    write_rgb16_png(subject_srgb, subject_finished_path, ffmpeg, working_profile)
    write_rgb16_png(subject_under, subject_under_path, ffmpeg, working_profile)
    write_rgb16_png(background_srgb_pixels, background_srgb_path, ffmpeg, working_profile)

    background_working = _scaled_rgb16(
        background_srgb_path, working_width, working_height, ffmpeg
    )
    subject_working = _scaled_rgb16(
        subject_finished_path, working_width, working_height, ffmpeg
    )
    alpha_working = _scaled_alpha16(subject_png, working_width, working_height, ffmpeg)

    return LayeredWorkingSources(
        layered_tiff=layered_tiff,
        subject_png=subject_png,
        background_png=background_png,
        subject_finished=subject_finished_path,
        subject_under_resolved=subject_under_path,
        background_srgb=background_srgb_path,
        background_pixels=background_working,
        subject_pixels=subject_working,
        subject_alpha=alpha_working,
        provenance={
            "layeredTiff": str(layered_tiff.resolve()),
            "layeredTiffSha256": _sha256(layered_tiff),
            "layeredTiffBitsPerChannel": 16,
            "layeredTiffProfile": subject_profile_name,
            "workingLayerProfileSource": (
                "The Photoshop PNG working copies contain the unconverted layer pixels; "
                f"their {layered_profile_name} profile is inherited from the authoritative layered TIFF."
            ),
            "layerNames": ["Subject", "Background"],
            "sourceWidth": int(subject_rgb.shape[1]),
            "sourceHeight": int(subject_rgb.shape[0]),
            "subjectLayer": str(subject_png.resolve()),
            "subjectLayerSha256": _sha256(subject_png),
            "backgroundLayer": str(background_png.resolve()),
            "backgroundLayerSha256": _sha256(background_png),
            "subjectAlphaMinimum": int(subject_alpha.min()),
            "subjectAlphaMaximum": int(subject_alpha.max()),
            "workingProfile": "sRGB IEC61966-2.1",
            "precisionPolicy": "16-bit layer extraction, ICC conversion, effect generation, development compositing, and background compositing; 8-bit only at H.264 delivery encode",
        },
    )


def _blur_mask(mask: Any, radius: float) -> Any:
    np = _numpy()
    image = Image.fromarray(np.rint(np.clip(mask, 0, 1) * 255).astype("uint8"), "L")
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(blurred, dtype=np.float32) / 255.0


def _shift_mask(mask: Any, dx: int, dy: int) -> Any:
    np = _numpy()
    output = np.zeros_like(mask)
    source_x0 = max(0, -dx)
    source_x1 = mask.shape[1] - max(0, dx)
    source_y0 = max(0, -dy)
    source_y1 = mask.shape[0] - max(0, dy)
    target_x0 = max(0, dx)
    target_x1 = target_x0 + max(0, source_x1 - source_x0)
    target_y0 = max(0, dy)
    target_y1 = target_y0 + max(0, source_y1 - source_y0)
    if source_x1 > source_x0 and source_y1 > source_y0:
        output[target_y0:target_y1, target_x0:target_x1] = mask[
            source_y0:source_y1, source_x0:source_x1
        ]
    return output


def _oriented_gaussian(
    x: Any,
    y: Any,
    *,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    angle: float = 0.0,
) -> Any:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    translated_x = x - center_x
    translated_y = y - center_y
    rotated_x = translated_x * cosine + translated_y * sine
    rotated_y = -translated_x * sine + translated_y * cosine
    return _numpy().exp(
        -0.5 * ((rotated_x / radius_x) ** 2 + (rotated_y / radius_y) ** 2)
    )


def _geometry_masks(width: int, height: int) -> list[Any]:
    np = _numpy()
    scale = 2
    masks = []
    for group in range(3):
        image = Image.new("L", (width * scale, height * scale), 0)
        draw = ImageDraw.Draw(image)
        line_width = max(2, round(width * 0.004 * scale))
        if group == 0:
            draw.arc(
                (
                    int(width * 0.03 * scale),
                    int(height * 0.23 * scale),
                    int(width * 0.48 * scale),
                    int(height * 0.53 * scale),
                ),
                198,
                494,
                fill=255,
                width=line_width,
            )
        elif group == 1:
            draw.arc(
                (
                    int(width * 0.26 * scale),
                    int(height * 0.02 * scale),
                    int(width * 0.96 * scale),
                    int(height * 0.43 * scale),
                ),
                205,
                338,
                fill=255,
                width=line_width,
            )
            draw.line(
                (
                    int(width * 0.08 * scale),
                    int(height * 0.16 * scale),
                    int(width * 0.88 * scale),
                    int(height * 0.09 * scale),
                ),
                fill=170,
                width=max(1, line_width // 2),
            )
        else:
            for point_x, point_y, radius in (
                (0.07, 0.08, 0.012),
                (0.52, 0.055, 0.009),
                (0.92, 0.29, 0.014),
                (0.18, 0.61, 0.009),
                (0.88, 0.68, 0.011),
            ):
                x = int(point_x * width * scale)
                y = int(point_y * height * scale)
                r = max(2, int(radius * width * scale))
                draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        image = image.filter(ImageFilter.GaussianBlur(radius=0.35))
        masks.append(np.asarray(image, dtype=np.float32) / 255.0)
    return masks


def build_background_context(
    background_pixels: Any,
    subject_pixels: Any,
    subject_alpha: Any,
) -> dict[str, Any]:
    np = _numpy()
    background = np.asarray(background_pixels, dtype=np.float32) / 65535.0
    subject = np.asarray(subject_pixels, dtype=np.float32) / 65535.0
    alpha = np.asarray(subject_alpha, dtype=np.float32) / 65535.0
    height, width = alpha.shape
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    x /= max(width - 1, 1)
    y /= max(height - 1, 1)
    luminance = subject.mean(axis=2)
    skin_candidates = (
        (alpha > 0.65)
        & (subject[:, :, 0] > subject[:, :, 1] * 1.04)
        & (subject[:, :, 1] > subject[:, :, 2] * 1.02)
        & (luminance > 0.30)
    )
    dark_candidates = (alpha > 0.65) & (luminance < 0.26)
    skin_color = (
        np.median(subject[skin_candidates], axis=0)
        if skin_candidates.any()
        else np.asarray([0.72, 0.56, 0.46], dtype=np.float32)
    )
    dark_color = (
        np.median(subject[dark_candidates], axis=0)
        if dark_candidates.any()
        else np.asarray([0.10, 0.10, 0.12], dtype=np.float32)
    )
    return {
        "background": background,
        "alpha": alpha,
        "alphaSoft": _blur_mask(alpha, max(2.0, width * 0.028)),
        "alphaGhost": _blur_mask(alpha, max(1.0, width * 0.012)),
        "x": x,
        "y": y,
        "skinColor": np.asarray(skin_color, dtype=np.float32),
        "darkColor": np.asarray(dark_color, dtype=np.float32),
        "geometryMasks": _geometry_masks(width, height),
    }


def _mix_color(base: Any, color: Any, amount: Any) -> Any:
    np = _numpy()
    opacity = np.clip(amount, 0.0, 0.35)[:, :, None]
    return base * (1.0 - opacity) + np.asarray(color, dtype=np.float32) * opacity


def background_effect_frame(
    recipe: InfinityBackgroundRecipe,
    fraction: float,
    context: dict[str, Any],
) -> Any:
    np = _numpy()
    base = context["background"]
    x = context["x"]
    y = context["y"]
    envelope = math.sin(math.pi * max(0.0, min(1.0, fraction))) ** 2
    phase = 2.0 * math.pi * fraction * recipe.speed
    strength = recipe.strength * envelope
    warm_neutral = context["skinColor"] * 0.42 + np.asarray(
        [0.88, 0.86, 0.82], dtype=np.float32
    ) * 0.58
    quiet_dark = context["darkColor"] * 0.30 + np.asarray(
        [0.50, 0.49, 0.47], dtype=np.float32
    ) * 0.70

    if recipe.effect == "momentum_wake":
        field = _oriented_gaussian(
            x,
            y,
            center_x=0.34 + 0.035 * math.sin(phase),
            center_y=0.50 + 0.025 * math.cos(phase),
            radius_x=0.48,
            radius_y=0.17,
            angle=-0.42,
        )
        frame = _mix_color(base, warm_neutral, field * strength)
    elif recipe.effect == "emulsion_bloom":
        field = np.zeros_like(x)
        for center_x, center_y, radius_x, radius_y, offset, weight in (
            (0.18, 0.20, 0.28, 0.18, 0.0, 0.80),
            (0.72, 0.35, 0.34, 0.23, 1.7, 0.62),
            (0.36, 0.72, 0.38, 0.25, 3.2, 0.58),
            (0.86, 0.82, 0.25, 0.20, 4.6, 0.48),
        ):
            field += weight * _oriented_gaussian(
                x,
                y,
                center_x=center_x + 0.025 * math.sin(phase + offset),
                center_y=center_y + 0.020 * math.cos(phase * 0.9 + offset),
                radius_x=radius_x,
                radius_y=radius_y,
                angle=0.2 * math.sin(offset),
            )
        field /= max(float(field.max()), 1e-6)
        frame = _mix_color(base, warm_neutral * 0.92, field * strength)
    elif recipe.effect == "floating_print":
        dx = int(round(7 + 3 * math.sin(phase)))
        dy = int(round(10 + 2 * math.cos(phase)))
        shadow = _shift_mask(context["alphaSoft"], dx, dy)
        frame = _mix_color(base, quiet_dark, shadow * strength)
    elif recipe.effect == "negative_space_aperture":
        aperture = _oriented_gaussian(
            x,
            y,
            center_x=0.64 + 0.08 * math.sin(phase),
            center_y=0.27 + 0.05 * math.cos(phase),
            radius_x=0.42,
            radius_y=0.30,
            angle=-0.18,
        )
        outer_density = np.clip(1.0 - aperture, 0.0, 1.0)
        frame = _mix_color(base, quiet_dark * 0.82 + warm_neutral * 0.18, outer_density * strength)
    elif recipe.effect == "residual_gesture":
        ghost_a = _shift_mask(
            context["alphaGhost"],
            int(round(-15 - 3 * math.sin(phase))),
            int(round(3 + 2 * math.cos(phase))),
        )
        ghost_b = _shift_mask(
            context["alphaGhost"],
            int(round(12 + 2 * math.cos(phase))),
            int(round(-5 + 2 * math.sin(phase))),
        )
        ghost = np.clip(ghost_a * 0.70 + ghost_b * 0.35, 0.0, 1.0)
        frame = _mix_color(base, warm_neutral * 0.72 + quiet_dark * 0.28, ghost * strength)
    elif recipe.effect == "incomplete_geometry":
        masks = context["geometryMasks"]
        weights = [
            max(0.0, math.sin(math.pi * fraction + offset)) ** 2
            for offset in (0.0, 0.65, 1.25)
        ]
        geometry = np.clip(
            masks[0] * weights[0] + masks[1] * weights[1] + masks[2] * weights[2],
            0.0,
            1.0,
        )
        frame = _mix_color(base, quiet_dark, geometry * strength)
    elif recipe.effect == "borrowed_color_field":
        skin_field = _oriented_gaussian(
            x,
            y,
            center_x=0.27 + 0.04 * math.sin(phase),
            center_y=0.30 + 0.03 * math.cos(phase),
            radius_x=0.42,
            radius_y=0.27,
            angle=0.28,
        )
        dark_field = _oriented_gaussian(
            x,
            y,
            center_x=0.72 + 0.035 * math.cos(phase),
            center_y=0.73 + 0.025 * math.sin(phase),
            radius_x=0.46,
            radius_y=0.30,
            angle=-0.22,
        )
        frame = _mix_color(base, context["skinColor"], skin_field * strength * 0.72)
        frame = _mix_color(frame, context["darkColor"] * 0.55 + base.mean(axis=(0, 1)) * 0.45, dark_field * strength * 0.48)
    else:  # pragma: no cover - configuration validation prevents this
        raise ValueError(recipe.effect)

    return np.rint(np.clip(frame, 0.0, 1.0) * 65535.0).astype("<u2")


def render_background_intermediate(
    *,
    recipe: InfinityBackgroundRecipe,
    context: dict[str, Any],
    frames: int,
    fps: int,
    output: Path,
    ffmpeg: str,
) -> dict[str, Any]:
    np = _numpy()
    output.parent.mkdir(parents=True, exist_ok=True)
    height, width = context["alpha"].shape
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb48le",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-pix_fmt",
        "gbrp16le",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:  # pragma: no cover - defensive
        process.kill()
        raise RuntimeError("Background frame pipe was unavailable")
    first_bytes: bytes | None = None
    last_bytes: bytes | None = None
    timeline = []
    base = np.asarray(context["background"] * 65535.0, dtype=np.float32)
    try:
        for frame_index in range(frames):
            fraction = frame_index / max(frames - 1, 1)
            pixels = background_effect_frame(recipe, fraction, context)
            if frame_index == frames - 1 and first_bytes is not None:
                frame_bytes = first_bytes
                pixels = np.frombuffer(frame_bytes, dtype="<u2").reshape(height, width, 3)
            else:
                frame_bytes = pixels.tobytes()
            if first_bytes is None:
                first_bytes = frame_bytes
            last_bytes = frame_bytes
            process.stdin.write(frame_bytes)
            timeline.append(
                {
                    "frame": frame_index,
                    "timeFraction": round(fraction, 6),
                    "meanAbsoluteBackgroundDelta": round(
                        float(np.abs(pixels.astype(np.float32) - base).mean() / 65535.0),
                        6,
                    ),
                }
            )
        process.stdin.close()
        return_code = process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)
    if first_bytes != last_bytes:
        raise AssertionError(f"{recipe.id} background does not close exactly")
    return {
        "firstLastBackgroundIdentical": True,
        "backgroundFrameSha256": hashlib.sha256(first_bytes or b"").hexdigest(),
        "frameTimeline": timeline,
    }


def build_infinity_background_filter(
    video_config: Config,
    mask_width: int,
    mask_height: int,
) -> str:
    render_width = video_config.width * 2
    render_height = video_config.height * 2
    return (
        f"[0:v]scale={render_width}:{render_height}:force_original_aspect_ratio=increase,"
        f"crop={render_width}:{render_height},format=gbrp16le[subjectFinal];"
        f"[1:v]scale={render_width}:{render_height}:force_original_aspect_ratio=increase,"
        f"crop={render_width}:{render_height},format=gbrp16le[subjectUnder];"
        f"[2:v]scale={render_width}:{render_height}:flags=bicubic,format=gray16le[developmentMask];"
        f"[subjectUnder][subjectFinal][developmentMask]maskedmerge[developedSubject];"
        f"[3:v]scale={render_width}:{render_height}:flags=lanczos,format=gbrp16le[animatedBackground];"
        f"[4:v]scale={render_width}:{render_height}:force_original_aspect_ratio=increase,"
        f"crop={render_width}:{render_height},format=rgba64le,alphaextract,"
        f"format=gray16le[subjectAlpha];"
        f"[animatedBackground][developedSubject][subjectAlpha]maskedmerge,"
        f"scale={video_config.width}:{video_config.height}:flags=lanczos,"
        f"fps={video_config.fps},format={video_config.pixel_format},"
        f"setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709[out]"
    )


def render_composite_candidate(
    *,
    video_config: Config,
    subject_finished: Path,
    subject_under_resolved: Path,
    subject_rgba: Path,
    background_intermediate: Path,
    masks: list[bytes],
    mask_width: int,
    mask_height: int,
    output: Path,
    ffmpeg: str,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = len(masks)
    filter_graph = build_infinity_background_filter(
        video_config, mask_width, mask_height
    )
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        str(video_config.fps),
        "-loop",
        "1",
        "-i",
        str(subject_finished),
        "-framerate",
        str(video_config.fps),
        "-loop",
        "1",
        "-i",
        str(subject_under_resolved),
        "-f",
        "rawvideo",
        "-pixel_format",
        "gray",
        "-video_size",
        f"{mask_width}x{mask_height}",
        "-framerate",
        str(video_config.fps),
        "-i",
        "pipe:0",
        "-i",
        str(background_intermediate),
        "-framerate",
        str(video_config.fps),
        "-loop",
        "1",
        "-i",
        str(subject_rgba),
        "-filter_complex",
        filter_graph,
        "-map",
        "[out]",
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        video_config.codec,
        "-crf",
        "18",
        "-preset",
        "medium",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:  # pragma: no cover - defensive
        process.kill()
        raise RuntimeError("Development mask pipe was unavailable")
    try:
        for mask in masks:
            process.stdin.write(mask)
        process.stdin.close()
        return_code = process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def development_state(
    *,
    recipe: DevelopmentRecipe,
    development_config: DevelopmentConfig,
    seed: int,
    frames: int,
    focal_point: tuple[float, float],
) -> tuple[list[bytes], list[dict[str, Any]], dict[str, Any]]:
    mask_width = int(development_config.mask["width"])
    mask_height = int(development_config.mask["height"])
    masks, timeline = development_mask_frames(
        recipe,
        seed=seed,
        frames=frames,
        width=mask_width,
        height=mask_height,
        focal_point=focal_point,
        mask_settings=development_config.mask,
    )
    digest = hashlib.sha256()
    for mask in masks:
        digest.update(mask)
    field = {
        "maskWidth": mask_width,
        "maskHeight": mask_height,
        "focalPoint": {"x": round(focal_point[0], 6), "y": round(focal_point[1], 6)},
        "backgroundInfluence": development_config.mask["backgroundInfluence"],
        "baseFinalMix": recipe.base_final_mix,
        "patchCount": recipe.patch_count,
        "patchSizeRange": [recipe.patch_size_min, recipe.patch_size_max],
        "feather": recipe.feather,
        "neighborCoupling": recipe.neighbor_coupling,
        "speed": recipe.speed,
        "direction": recipe.direction,
        "finishedHold": recipe.finished_hold,
        "easePower": recipe.ease_power,
        "algorithm": "seeded periodic broad field",
        "maskStreamSha256": digest.hexdigest(),
        "firstLastMaskIdentical": masks[0] == masks[-1],
    }
    return masks, timeline, field
