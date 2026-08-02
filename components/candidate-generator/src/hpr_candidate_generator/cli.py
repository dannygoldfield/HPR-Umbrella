from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .generator import build_plan, generate_candidate


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AUDIO_RECIPES = {7: "AR-008", 9: "AR-009", 11: "AR-010"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hpr-candidate",
        description="Plan or generate review candidates for How People Relate",
    )
    parser.add_argument("command", choices=["plan", "generate"])
    parser.add_argument("--portrait", required=True, type=Path)
    parser.add_argument("--grain", required=True, type=Path)
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
