from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .generator import build_plan, generate_candidate
from .engine import (
    ArchiveProductionSpec,
    DEFAULT_VISUAL_PRESETS,
    build_archive_plan,
    load_portraits_csv,
    write_archive_plan,
)


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AUDIO_RECIPES = {7: "AR-008", 9: "AR-009", 11: "AR-010"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hpr-candidate",
        description="Plan or generate review candidates for How People Relate",
    )
    parser.add_argument("command", choices=["plan", "generate", "archive-plan"])
    parser.add_argument("--portrait", type=Path)
    parser.add_argument("--grain", type=Path)
    parser.add_argument("--portraits-csv", type=Path)
    parser.add_argument("--expected-episodes", type=int, default=120)
    parser.add_argument("--audio-per-duration", type=int, default=50)
    parser.add_argument(
        "--visual-presets",
        default=",".join(DEFAULT_VISUAL_PRESETS),
        help="comma-separated preset IDs; one visual candidate is planned per preset",
    )
    parser.add_argument("--duration", type=int, choices=[7, 9, 11], default=7)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--video-preset", default="VP-002")
    parser.add_argument("--audio-recipe")
    parser.add_argument("--output", type=Path, default=Path("workspace/output"))
    parser.add_argument(
        "--video-config",
        type=Path,
        default=ROOT / "components/video-generator/config/generator.xml",
    )
    parser.add_argument(
        "--audio-config",
        type=Path,
        default=ROOT / "components/audio-generator/config/generator.xml",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "archive-plan":
        if args.portraits_csv is None:
            raise SystemExit("archive-plan requires --portraits-csv")
        presets = tuple(value.strip() for value in args.visual_presets.split(",") if value.strip())
        spec = ArchiveProductionSpec(
            episode_count=args.expected_episodes,
            visual_candidates_per_episode=len(presets),
            audio_tracks_per_duration=args.audio_per_duration,
            visual_presets=presets,
        )
        plan = build_archive_plan(load_portraits_csv(args.portraits_csv), args.seed, spec)
        paths = write_archive_plan(plan, args.output)
        print(paths["summary"])
        return
    if args.portrait is None or args.grain is None:
        raise SystemExit(f"{args.command} requires --portrait and --grain")
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    for index in range(args.count):
        audio_recipe = args.audio_recipe or DEFAULT_AUDIO_RECIPES[args.duration]
        plan = build_plan(
            portrait=args.portrait,
            grain=args.grain,
            duration_sec=args.duration,
            seed=args.seed + index,
            video_preset=args.video_preset,
            audio_recipe=audio_recipe,
            output_root=args.output,
        )
        if args.command == "plan":
            payload = {
                key: str(value) if isinstance(value, Path) else value
                for key, value in asdict(plan).items()
            }
            print(json.dumps(payload, indent=2))
        else:
            result = generate_candidate(plan, args.video_config, args.audio_config)
            print(result.plan.final_video)


if __name__ == "__main__":
    main()
