from __future__ import annotations

import argparse
import json
from pathlib import Path

from .registry import (
    create_sequence,
    get_sequence,
    ingest_metadata_report,
    initialize_registry,
    list_portraits,
    lock_sequence,
    set_sequence_order,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hpr-registry")
    parser.add_argument(
        "command",
        choices=(
            "init",
            "ingest-metadata-report",
            "list-portraits",
            "create-sequence",
            "set-sequence-order",
            "show-sequence",
            "lock-sequence",
        ),
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--intake-config", type=Path)
    parser.add_argument("--manifest-root", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--expected-count", type=int, default=120)
    parser.add_argument("--sequence-id")
    parser.add_argument("--master-ids", type=Path)
    return parser


def _read_master_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        values = json.loads(text)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError("Master ID JSON must be an array of strings")
        return values
    return [line.strip() for line in text.splitlines() if line.strip()]


def main() -> None:
    args = _parser().parse_args()
    if args.command == "init":
        initialize_registry(args.db)
        print(args.db)
        return
    if args.command == "ingest-metadata-report":
        required = (args.report, args.intake_config, args.manifest_root)
        if any(value is None for value in required):
            raise SystemExit(
                "ingest-metadata-report requires --report, --intake-config, and --manifest-root"
            )
        result = ingest_metadata_report(
            args.db, args.report, args.intake_config, args.manifest_root
        )
        print(json.dumps(result, indent=2))
        return
    if args.command == "list-portraits":
        print(json.dumps(list_portraits(args.db), indent=2))
        return
    if args.command == "create-sequence":
        if not args.name:
            raise SystemExit("create-sequence requires --name")
        print(create_sequence(args.db, args.name, args.expected_count))
        return
    if not args.sequence_id:
        raise SystemExit(f"{args.command} requires --sequence-id")
    if args.command == "set-sequence-order":
        if args.master_ids is None:
            raise SystemExit("set-sequence-order requires --master-ids")
        set_sequence_order(args.db, args.sequence_id, _read_master_ids(args.master_ids))
        print(args.sequence_id)
    elif args.command == "show-sequence":
        print(json.dumps(get_sequence(args.db, args.sequence_id), indent=2))
    elif args.command == "lock-sequence":
        lock_sequence(args.db, args.sequence_id)
        print(args.sequence_id)


if __name__ == "__main__":
    main()
