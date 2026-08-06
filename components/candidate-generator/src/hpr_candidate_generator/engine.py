from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import csv
import hashlib
import json
from pathlib import Path
import random
from typing import Iterable, Mapping, Sequence


ARCHIVE_DURATIONS = (7, 9, 11)
DEFAULT_VISUAL_PRESETS = ("VP-022", "VP-023", "VP-024", "VP-030", "VP-031")
DEFAULT_AUDIO_RECIPES = {7: "AR-008", 9: "AR-009", 11: "AR-010"}


@dataclass(frozen=True)
class ArchiveProductionSpec:
    episode_count: int = 120
    visual_candidates_per_episode: int = 5
    audio_tracks_per_duration: int = 50
    pair_options_per_episode: int = 10
    durations: tuple[int, ...] = ARCHIVE_DURATIONS
    visual_presets: tuple[str, ...] = DEFAULT_VISUAL_PRESETS

    def validate(self) -> None:
        if self.episode_count < 1:
            raise ValueError("episode_count must be positive")
        if self.visual_candidates_per_episode != len(self.visual_presets):
            raise ValueError("visual preset count must equal visual_candidates_per_episode")
        if self.episode_count % len(self.durations):
            raise ValueError("episode_count must divide evenly across durations")
        if self.audio_tracks_per_duration < self.episode_count // len(self.durations):
            raise ValueError("audio bank must contain at least one unique track per episode")


@dataclass(frozen=True)
class PortraitInput:
    portrait_id: str
    path: Path


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    mode: str
    duration_sec: int
    portrait_id: str
    portrait_path: str
    photo_revision: int = 1
    selected_visual_id: str | None = None
    selected_visual_recipe: str | None = None
    selected_audio_id: str | None = None
    selected_pair_id: str | None = None
    text_treatment_id: str | None = None
    status: str = "awaiting_visual_review"
    renders_stale: bool = False
    publication_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualCandidateRecord:
    visual_id: str
    episode_id: str
    portrait_id: str
    portrait_path: str
    photo_revision: int
    duration_sec: int
    preset_id: str
    seed: int
    status: str = "planned"
    rating: int | None = None
    note: str = ""


@dataclass(frozen=True)
class AudioCandidateRecord:
    audio_id: str
    duration_sec: int
    recipe_id: str
    seed: int
    status: str = "planned"
    rating: int | None = None
    note: str = ""


@dataclass(frozen=True)
class PairCandidateRecord:
    pair_id: str
    episode_id: str
    visual_id: str
    audio_id: str
    duration_sec: int
    status: str = "planned"
    visual_rating: int | None = None
    audio_rating: int | None = None
    pair_rating: int | None = None
    note: str = ""


@dataclass(frozen=True)
class PublishingRecord:
    episode_id: str
    pair_id: str | None = None
    audio_id: str | None = None
    master_path: str | None = None
    text_treatment_id: str | None = None
    status: str = "not_ready"


@dataclass(frozen=True)
class ArchivePlan:
    spec: ArchiveProductionSpec
    seed: int
    episodes: tuple[EpisodeRecord, ...]
    visuals: tuple[VisualCandidateRecord, ...]
    audio: tuple[AudioCandidateRecord, ...]
    pairs: tuple[PairCandidateRecord, ...]
    publishing: tuple[PublishingRecord, ...]


def load_portraits_csv(path: Path) -> list[PortraitInput]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    required = {"portrait_id", "path"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("portrait CSV requires portrait_id and path columns")
    portraits = [PortraitInput(row["portrait_id"].strip(), Path(row["path"].strip())) for row in rows]
    if any(not portrait.portrait_id or not str(portrait.path) for portrait in portraits):
        raise ValueError("portrait_id and path cannot be blank")
    if len({portrait.portrait_id for portrait in portraits}) != len(portraits):
        raise ValueError("portrait_id values must be unique")
    return portraits


def _derived_seed(seed: int, *parts: object) -> int:
    payload = ":".join([str(seed), *(str(part) for part in parts)]).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def build_archive_plan(
    portraits: Sequence[PortraitInput],
    seed: int,
    spec: ArchiveProductionSpec | None = None,
) -> ArchivePlan:
    spec = spec or ArchiveProductionSpec()
    spec.validate()
    if len(portraits) != spec.episode_count:
        raise ValueError(f"expected {spec.episode_count} portraits, received {len(portraits)}")

    episodes: list[EpisodeRecord] = []
    visuals: list[VisualCandidateRecord] = []
    publishing: list[PublishingRecord] = []
    per_duration = spec.episode_count // len(spec.durations)

    for index, portrait in enumerate(portraits, start=1):
        duration = spec.durations[(index - 1) // per_duration]
        episode_id = f"ARC-{index:03d}"
        episodes.append(
            EpisodeRecord(
                episode_id=episode_id,
                mode="archive",
                duration_sec=duration,
                portrait_id=portrait.portrait_id,
                portrait_path=str(portrait.path),
            )
        )
        publishing.append(PublishingRecord(episode_id=episode_id))
        for option, preset_id in enumerate(spec.visual_presets, start=1):
            visuals.append(
                VisualCandidateRecord(
                    visual_id=f"VIS-{episode_id}-{option:02d}",
                    episode_id=episode_id,
                    portrait_id=portrait.portrait_id,
                    portrait_path=str(portrait.path),
                    photo_revision=1,
                    duration_sec=duration,
                    preset_id=preset_id,
                    seed=_derived_seed(seed, episode_id, preset_id),
                )
            )

    audio = tuple(
        AudioCandidateRecord(
            audio_id=f"AUD-{duration:03d}-{index:03d}",
            duration_sec=duration,
            recipe_id=DEFAULT_AUDIO_RECIPES[duration],
            seed=_derived_seed(seed, "audio", duration, index),
        )
        for duration in spec.durations
        for index in range(1, spec.audio_tracks_per_duration + 1)
    )
    return ArchivePlan(
        spec=spec,
        seed=seed,
        episodes=tuple(episodes),
        visuals=tuple(visuals),
        audio=audio,
        pairs=(),
        publishing=tuple(publishing),
    )


def plan_pair_options(
    episode: EpisodeRecord,
    audio_bank: Sequence[AudioCandidateRecord],
    count: int,
    seed: int,
) -> tuple[PairCandidateRecord, ...]:
    if not episode.selected_visual_id:
        raise ValueError("a visual must be selected before audio pairings are planned")
    available = [
        audio
        for audio in audio_bank
        if audio.duration_sec == episode.duration_sec and audio.status not in {"retired", "published"}
    ]
    if len(available) < count:
        raise ValueError(f"need {count} available audio tracks, found {len(available)}")
    rng = random.Random(_derived_seed(seed, episode.episode_id, episode.selected_visual_id))
    chosen = rng.sample(available, count)
    return tuple(
        PairCandidateRecord(
            pair_id=f"PAIR-{episode.episode_id}-{index:02d}",
            episode_id=episode.episode_id,
            visual_id=episode.selected_visual_id,
            audio_id=audio.audio_id,
            duration_sec=episode.duration_sec,
        )
        for index, audio in enumerate(chosen, start=1)
    )


def replace_episode_photo(episode: EpisodeRecord, portrait_id: str, portrait_path: Path) -> EpisodeRecord:
    return replace(
        episode,
        portrait_id=portrait_id,
        portrait_path=str(portrait_path),
        photo_revision=episode.photo_revision + 1,
        renders_stale=True,
    )


def record_pair_review(
    pair: PairCandidateRecord,
    *,
    visual_rating: int | None = None,
    audio_rating: int | None = None,
    pair_rating: int | None = None,
    status: str | None = None,
    note: str | None = None,
) -> PairCandidateRecord:
    for label, rating in (
        ("visual_rating", visual_rating),
        ("audio_rating", audio_rating),
        ("pair_rating", pair_rating),
    ):
        if rating is not None and rating not in range(0, 6):
            raise ValueError(f"{label} must be between 0 and 5")
    return replace(
        pair,
        visual_rating=visual_rating if visual_rating is not None else pair.visual_rating,
        audio_rating=audio_rating if audio_rating is not None else pair.audio_rating,
        pair_rating=pair_rating if pair_rating is not None else pair.pair_rating,
        status=status or pair.status,
        note=note if note is not None else pair.note,
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def write_jsonl(path: Path, records: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(_jsonable(asdict(record)), sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_archive_plan(plan: ArchivePlan, output_root: Path) -> Mapping[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    banks = output_root / "banks"
    paths = {
        "episodes": banks / "episodes.jsonl",
        "visual": banks / "visual.jsonl",
        "audio": banks / "audio.jsonl",
        "pair": banks / "pair.jsonl",
        "publishing": banks / "publishing.jsonl",
        "summary": output_root / "archive-production-plan.json",
    }
    write_jsonl(paths["episodes"], plan.episodes)
    write_jsonl(paths["visual"], plan.visuals)
    write_jsonl(paths["audio"], plan.audio)
    write_jsonl(paths["pair"], plan.pairs)
    write_jsonl(paths["publishing"], plan.publishing)
    summary = {
        "mode": "archive",
        "now_mode": "deferred",
        "seed": plan.seed,
        "spec": _jsonable(asdict(plan.spec)),
        "counts": {
            "episodes": len(plan.episodes),
            "visual_candidates": len(plan.visuals),
            "audio_candidates": len(plan.audio),
            "pair_candidates": len(plan.pairs),
            "publishing_slots": len(plan.publishing),
        },
        "banks": {key: str(path) for key, path in paths.items() if key != "summary"},
    }
    paths["summary"].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return paths
