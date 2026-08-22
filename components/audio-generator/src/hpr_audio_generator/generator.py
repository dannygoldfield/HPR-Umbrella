from __future__ import annotations

from array import array
from dataclasses import dataclass
from math import cos, pi, pow, sin
from pathlib import Path
import random
import wave

from .config import Asset, Config


@dataclass(frozen=True)
class GeneratedTrack:
    path: Path
    seed: int
    recipe_id: str
    bed_id: str
    bed_start_sec: float
    gesture_id: str
    gesture_start_sec: float
    music_stem_id: str | None = None
    music_start_sec: float | None = None


def _read_pcm(asset: Asset, config: Config) -> array:
    with wave.open(str(asset.path), "rb") as source:
        actual = (source.getframerate(), source.getnchannels(), source.getsampwidth() * 8)
        expected = (config.sample_rate, config.channels, config.sample_width_bits)
        if actual != expected:
            raise ValueError(f"{asset.asset_id} format {actual} does not match {expected}")
        samples = array("h")
        samples.frombytes(source.readframes(source.getnframes()))
        return samples


def _gain(samples: array, gain_db: float) -> array:
    factor = pow(10.0, gain_db / 20.0)
    return array("h", (max(-32768, min(32767, round(value * factor))) for value in samples))


def _fit_bed(samples: array, target_samples: int) -> array:
    if not samples:
        raise ValueError("Bed contains no samples")
    repeats = (target_samples + len(samples) - 1) // len(samples)
    return array("h", (samples * repeats)[:target_samples])


def _music_excerpt(samples: array, target_samples: int, extra_samples: int, channels: int, sample_rate: int, rng: random.Random) -> tuple[array, float]:
    if not samples:
        raise ValueError("Music stem contains no samples")
    required_samples = target_samples + extra_samples
    if len(samples) < required_samples:
        return _fit_bed(samples, required_samples), 0.0
    max_start_frame = (len(samples) - target_samples) // channels
    start_frame = rng.randint(0, max_start_frame)
    start = start_frame * channels
    excerpt = array("h", samples[start:start + required_samples])
    if len(excerpt) < required_samples:
        excerpt.extend(samples[:required_samples - len(excerpt)])
    return excerpt, start_frame / sample_rate


def _best_loop_excerpt(
    samples: array,
    target_samples: int,
    extra_samples: int,
    channels: int,
    sample_rate: int,
    step_sec: float,
) -> tuple[array, float]:
    """Choose an excerpt whose post-loop continuation most closely matches its start."""
    if not samples:
        raise ValueError("Continuous layer contains no samples")
    required_samples = target_samples + extra_samples
    if len(samples) < required_samples:
        return _fit_bed(samples, required_samples), 0.0

    max_start_frame = (len(samples) - required_samples) // channels
    step_frames = max(1, round(step_sec * sample_rate))
    starts = list(range(0, max_start_frame + 1, step_frames))
    if starts[-1] != max_start_frame:
        starts.append(max_start_frame)
    comparison_stride = channels * 128

    def cost(start_frame: int) -> float:
        start = start_frame * channels
        continuation = start + target_samples
        squared_error = 0.0
        signal_energy = 1.0
        for offset in range(0, extra_samples, comparison_stride):
            for channel in range(channels):
                head = samples[start + offset + channel]
                tail = samples[continuation + offset + channel]
                difference = head - tail
                squared_error += difference * difference
                signal_energy += head * head + tail * tail
        return squared_error / signal_energy

    best_start_frame = min(starts, key=cost)
    best_start = best_start_frame * channels
    return (
        array("h", samples[best_start:best_start + required_samples]),
        best_start_frame / sample_rate,
    )


def _seamless_loop(
    samples: array,
    target_samples: int,
    fade_frames: int,
    channels: int,
    curve: str = "linear",
) -> array:
    if fade_frames <= 0:
        return array("h", samples[:target_samples])
    fade_samples = fade_frames * channels
    if len(samples) < target_samples + fade_samples:
        raise ValueError("Continuous layer is too short for loop crossfade")
    result = array("h", samples[:target_samples])
    denominator = max(1, fade_frames - 1)
    for frame in range(fade_frames):
        progress = frame / denominator
        if curve == "equalPower":
            tail_weight = cos(progress * pi / 2.0)
            head_weight = sin(progress * pi / 2.0)
        elif curve == "linear":
            tail_weight = 1.0 - progress
            head_weight = progress
        else:
            raise ValueError(f"Unknown loop curve: {curve}")
        head = frame * channels
        tail = target_samples + head
        for channel in range(channels):
            result[head + channel] = max(
                -32768,
                min(
                    32767,
                    round(
                        samples[tail + channel] * tail_weight
                        + samples[head + channel] * head_weight
                    ),
                ),
            )
    result[fade_samples:] = samples[fade_samples:target_samples]
    return result


def generate(config: Config, recipe_id: str, seed: int, output_path: Path) -> GeneratedTrack:
    recipe = config.recipes[recipe_id]
    profile = config.profiles[recipe.profile_id]
    rng = random.Random(seed)

    beds = [
        item for item in config.assets
        if item.role == "Bed" and item.status == "Active"
        and (recipe.bed_family is None or item.family == recipe.bed_family)
    ]
    gestures = [
        item for item in config.assets
        if item.role == "Gesture" and item.status == "Active"
        and (recipe.gesture_family is None or item.family == recipe.gesture_family)
    ]
    if not beds or not gestures:
        raise ValueError(f"{recipe_id} has no eligible bed or gesture")

    bed = rng.choice(beds)
    gesture = rng.choice(gestures)
    total_frames = recipe.duration_sec * config.sample_rate
    target_samples = total_frames * config.channels
    fade_frames = round(profile.loop_crossfade_sec * config.sample_rate)
    fade_samples = fade_frames * config.channels
    gained_bed = _gain(_read_pcm(bed, config), profile.bed_gain_db)
    if profile.optimize_loop_excerpt:
        bed_source, bed_start_sec = _best_loop_excerpt(
            gained_bed,
            target_samples,
            fade_samples,
            config.channels,
            config.sample_rate,
            profile.loop_search_step_sec,
        )
    else:
        bed_source = _fit_bed(gained_bed, target_samples + fade_samples)
        bed_start_sec = 0.0
    mix = _seamless_loop(
        bed_source,
        target_samples,
        fade_frames,
        config.channels,
        profile.loop_crossfade_curve,
    )
    gesture_samples = _gain(_read_pcm(gesture, config), profile.gesture_gain_db)

    earliest = profile.avoid_first_sec
    latest = max(earliest, recipe.duration_sec - profile.avoid_last_sec - len(gesture_samples) / config.channels / config.sample_rate)
    gesture_start_sec = rng.uniform(earliest, latest)

    music_stem = None
    music_start_sec = None
    if recipe.use_music_stem:
        music_stems = [
            item for item in config.assets
            if item.role == "Music" and item.status == "Active"
        ]
        music_stem = rng.choice(music_stems)
        gained_music = _gain(_read_pcm(music_stem, config), profile.music_gain_db)
        if profile.optimize_loop_excerpt:
            music_samples, music_start_sec = _best_loop_excerpt(
                gained_music,
                target_samples,
                fade_samples,
                config.channels,
                config.sample_rate,
                profile.loop_search_step_sec,
            )
        else:
            music_samples, music_start_sec = _music_excerpt(
                gained_music,
                target_samples,
                fade_samples,
                config.channels,
                config.sample_rate,
                rng,
            )
        music_samples = _seamless_loop(
            music_samples,
            target_samples,
            fade_frames,
            config.channels,
            profile.loop_crossfade_curve,
        )
        for index, value in enumerate(music_samples):
            mix[index] = max(-32768, min(32767, mix[index] + value))

    start = int(gesture_start_sec * config.sample_rate) * config.channels
    for index, value in enumerate(gesture_samples[: max(0, target_samples - start)]):
        mixed = mix[start + index] + value
        mix[start + index] = max(-32768, min(32767, mixed))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(config.channels)
        output.setsampwidth(config.sample_width_bits // 8)
        output.setframerate(config.sample_rate)
        output.writeframes(mix.tobytes())

    return GeneratedTrack(
        path=output_path,
        seed=seed,
        recipe_id=recipe_id,
        bed_id=bed.asset_id,
        bed_start_sec=bed_start_sec,
        gesture_id=gesture.asset_id,
        gesture_start_sec=gesture_start_sec,
        music_stem_id=music_stem.asset_id if music_stem else None,
        music_start_sec=music_start_sec,
    )
