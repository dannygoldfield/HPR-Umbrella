from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Sequence


SOURCE_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_registry(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = resources.files("hpr_registry").joinpath("schema.sql").read_text(
        encoding="utf-8"
    )
    with _connect(db_path) as connection:
        connection.executescript(schema)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(1, ?)",
            (_now(),),
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(visual_candidates)")
        }
        if "experiment_id" not in columns:
            connection.execute(
                """
                ALTER TABLE visual_candidates
                ADD COLUMN experiment_id TEXT NOT NULL DEFAULT 'unspecified'
                """
            )
        if "parent_visual_id" not in columns:
            connection.execute(
                """
                ALTER TABLE visual_candidates
                ADD COLUMN parent_visual_id TEXT REFERENCES visual_candidates(visual_id)
                """
            )
        connection.execute(
            """
            UPDATE visual_candidates
            SET experiment_id='motion-rhythm-pilot-v1'
            WHERE experiment_id='unspecified' AND motion_recipe_id LIKE 'MR-%'
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(2, ?)",
            (_now(),),
        )
        pair_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(pair_candidates)")
        }
        if "experiment_id" not in pair_columns:
            connection.execute(
                """
                ALTER TABLE pair_candidates
                ADD COLUMN experiment_id TEXT NOT NULL DEFAULT 'unspecified'
                """
            )
        connection.execute(
            """
            UPDATE pair_candidates
            SET experiment_id='pairing-nychildren-v27'
            WHERE experiment_id='unspecified'
              AND manifest_path LIKE '%/pairing-nychildren-v27/%'
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(3, ?)",
            (_now(),),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_project_id(code: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", code).strip("-").upper()
    return f"SRC-{normalized}"


def _portrait_id(code: str, original_base_filename: str) -> str:
    payload = f"{code.casefold()}\0{original_base_filename.casefold()}".encode("utf-8")
    return f"POR-{hashlib.sha256(payload).hexdigest()[:12].upper()}"


def _field_value(result: dict[str, Any], field: str) -> Any:
    locations = result.get("fields", {}).get(field, {}).get("locations", [])
    if not locations:
        return None
    xmp = [item for item in locations if item.get("tag", "").startswith("XMP:")]
    return (xmp[-1] if xmp else locations[-1]).get("value")


def _single(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def ingest_metadata_report(
    db_path: Path,
    report_path: Path,
    intake_config_path: Path,
    manifest_root: Path,
) -> list[dict[str, Any]]:
    """Ingest inspected JPEGs idempotently and preserve revision provenance."""
    initialize_registry(db_path)
    report = _load_json(report_path)
    config = _load_json(intake_config_path).get("files", {})
    if not isinstance(config, dict):
        raise ValueError("Intake configuration requires a 'files' object")

    outcomes: list[dict[str, Any]] = []
    with _connect(db_path) as connection:
        for result in report.get("results", []):
            path = Path(result["path"])
            filename = path.name
            settings = config.get(filename)
            if not settings:
                raise ValueError(f"Missing intake configuration for {filename}")
            code = settings.get("source_project_code")
            display_name = settings.get("source_project_display_name")
            portrait_group = settings.get("portrait_group")
            if not isinstance(code, str) or not SOURCE_CODE_RE.fullmatch(code):
                raise ValueError(
                    f"source_project_code for {filename} must be 1-32 ASCII letters, "
                    "numbers, underscores, or hyphens"
                )
            if not display_name or not portrait_group:
                raise ValueError(
                    f"{filename} requires source_project_display_name and portrait_group"
                )
            if not path.is_file():
                raise FileNotFoundError(path)

            project_id = _source_project_id(code)
            created_at = _now()
            connection.execute(
                """
                INSERT INTO source_projects(
                    source_project_id, code, display_name, created_at
                ) VALUES(?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET display_name=excluded.display_name
                """,
                (project_id, code, display_name, created_at),
            )
            original_base_filename = path.stem
            existing_portrait = connection.execute(
                """
                SELECT portrait_id, portrait_group FROM portraits
                WHERE source_project_id=? AND lower(original_base_filename)=lower(?)
                """,
                (project_id, original_base_filename),
            ).fetchone()
            if existing_portrait:
                portrait_id = existing_portrait["portrait_id"]
                if existing_portrait["portrait_group"] != portrait_group:
                    raise ValueError(
                        f"{filename} changes portrait_group for existing portrait {portrait_id}"
                    )
            else:
                portrait_id = _portrait_id(code, original_base_filename)
                connection.execute(
                    """
                    INSERT INTO portraits(
                        portrait_id, source_project_id, intake_filename,
                        original_base_filename, portrait_group, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        portrait_id,
                        project_id,
                        filename,
                        original_base_filename,
                        portrait_group,
                        created_at,
                    ),
                )

            file_hash = _sha256(path)
            existing = connection.execute(
                """
                SELECT revision_id, revision_number FROM portrait_revisions
                WHERE portrait_id=? AND sha256=?
                """,
                (portrait_id, file_hash),
            ).fetchone()
            if existing:
                outcomes.append(
                    {
                        "filename": filename,
                        "portrait_id": portrait_id,
                        "revision_id": existing["revision_id"],
                        "revision_number": existing["revision_number"],
                        "action": "unchanged",
                    }
                )
                continue

            revision_number = connection.execute(
                """
                SELECT COALESCE(MAX(revision_number), 0) + 1
                FROM portrait_revisions WHERE portrait_id=?
                """,
                (portrait_id,),
            ).fetchone()[0]
            revision_id = f"{portrait_id}-R{revision_number:03d}"
            manifest_path = manifest_root / portrait_id / f"R{revision_number:03d}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest = {
                "schema_version": "1.0",
                "portrait_id": portrait_id,
                "revision_id": revision_id,
                "revision_number": revision_number,
                "source_project": {"code": code, "display_name": display_name},
                "portrait_group": portrait_group,
                "source_file": {
                    "path": str(path.resolve()),
                    "filename": filename,
                    "sha256": file_hash,
                    "size_bytes": path.stat().st_size,
                },
                "metadata_inspection": result,
                "ingested_at": created_at,
            }
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            keywords = _field_value(result, "keywords") or []
            connection.execute(
                """
                INSERT INTO portrait_revisions(
                    revision_id, portrait_id, revision_number, file_path, sha256,
                    file_size_bytes, width, height, metadata_manifest_path,
                    source_value, title, caption, headline, alt_text,
                    extended_description, keywords_json, lightroom_rating,
                    lightroom_color_label, creator, copyright, created_at
                ) VALUES(
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    revision_id,
                    portrait_id,
                    revision_number,
                    str(path.resolve()),
                    file_hash,
                    path.stat().st_size,
                    result.get("image", {}).get("width"),
                    result.get("image", {}).get("height"),
                    str(manifest_path.resolve()),
                    _single(_field_value(result, "source")),
                    _single(_field_value(result, "title")),
                    _single(_field_value(result, "caption")),
                    _single(_field_value(result, "headline")),
                    _single(_field_value(result, "alt_text")),
                    _single(_field_value(result, "extended_description")),
                    json.dumps(keywords, ensure_ascii=False),
                    _single(_field_value(result, "rating")),
                    _single(_field_value(result, "color_label")),
                    _single(_field_value(result, "creator")),
                    _single(_field_value(result, "copyright")),
                    created_at,
                ),
            )
            connection.execute(
                "UPDATE portraits SET current_revision_number=? WHERE portrait_id=?",
                (revision_number, portrait_id),
            )
            outcomes.append(
                {
                    "filename": filename,
                    "portrait_id": portrait_id,
                    "revision_id": revision_id,
                    "revision_number": revision_number,
                    "action": "ingested",
                }
            )
    return outcomes


def list_portraits(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT p.portrait_id, sp.code AS source_project_code,
                   sp.display_name AS source_project_display_name,
                   p.intake_filename, p.original_base_filename,
                   p.portrait_group, p.current_revision_number, p.status
            FROM portraits p
            JOIN source_projects sp USING(source_project_id)
            ORDER BY p.created_at, p.portrait_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_current_portrait_revisions(db_path: Path) -> list[dict[str, Any]]:
    """Return the current renderable revision for every active portrait."""
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT p.portrait_id, p.intake_filename, p.original_base_filename,
                   p.portrait_group, sp.code AS source_project_code,
                   sp.display_name AS source_project_display_name,
                   pr.revision_id, pr.revision_number, pr.file_path, pr.sha256,
                   pr.width, pr.height
            FROM portraits p
            JOIN source_projects sp USING(source_project_id)
            JOIN portrait_revisions pr
              ON pr.portrait_id = p.portrait_id
             AND pr.revision_number = p.current_revision_number
            WHERE p.status = 'active'
            ORDER BY p.created_at, p.portrait_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def register_visual_candidate(
    db_path: Path,
    *,
    visual_id: str,
    portrait_id: str,
    revision_id: str,
    motion_recipe_id: str,
    experiment_id: str = "unspecified",
    parent_visual_id: str | None = None,
    duration_sec: float,
    seed: int,
    generator_version: str,
    media_path: Path,
    manifest_path: Path,
    status: str = "rendered",
) -> None:
    """Register a rendered visual idempotently without changing its provenance."""
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    initialize_registry(db_path)
    values = {
        "portrait_id": portrait_id,
        "revision_id": revision_id,
        "motion_recipe_id": motion_recipe_id,
        "experiment_id": experiment_id,
        "parent_visual_id": parent_visual_id,
        "duration_sec": float(duration_sec),
        "seed": seed,
        "generator_version": generator_version,
    }
    with _connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT portrait_id, revision_id, motion_recipe_id, experiment_id,
                   parent_visual_id, duration_sec, seed, generator_version
            FROM visual_candidates WHERE visual_id=?
            """,
            (visual_id,),
        ).fetchone()
        if existing:
            changed = [
                field
                for field, value in values.items()
                if existing[field] != value
            ]
            if changed:
                raise ValueError(
                    f"Visual candidate {visual_id} already has different provenance: "
                    + ", ".join(changed)
                )
            connection.execute(
                """
                UPDATE visual_candidates
                SET media_path=?, manifest_path=?, status=?
                WHERE visual_id=?
                """,
                (str(media_path.resolve()), str(manifest_path.resolve()), status, visual_id),
            )
            return
        revision = connection.execute(
            "SELECT portrait_id FROM portrait_revisions WHERE revision_id=?",
            (revision_id,),
        ).fetchone()
        if not revision:
            raise ValueError(f"Unknown portrait revision: {revision_id}")
        if revision["portrait_id"] != portrait_id:
            raise ValueError(f"Revision {revision_id} does not belong to {portrait_id}")
        if parent_visual_id:
            parent = connection.execute(
                """
                SELECT portrait_id, revision_id FROM visual_candidates
                WHERE visual_id=?
                """,
                (parent_visual_id,),
            ).fetchone()
            if not parent:
                raise ValueError(f"Unknown parent visual candidate: {parent_visual_id}")
            if (
                parent["portrait_id"] != portrait_id
                or parent["revision_id"] != revision_id
            ):
                raise ValueError(
                    f"Parent {parent_visual_id} does not use revision {revision_id}"
                )
        connection.execute(
            """
            INSERT INTO visual_candidates(
                visual_id, portrait_id, revision_id, motion_recipe_id,
                experiment_id, parent_visual_id, duration_sec, seed,
                generator_version, media_path, manifest_path, status, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visual_id,
                portrait_id,
                revision_id,
                motion_recipe_id,
                experiment_id,
                parent_visual_id,
                duration_sec,
                seed,
                generator_version,
                str(media_path.resolve()),
                str(manifest_path.resolve()),
                status,
                _now(),
            ),
        )


def list_visual_candidates_for_review(db_path: Path) -> list[dict[str, Any]]:
    """Return visual candidates with the latest human review state."""
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            WITH latest_review AS (
                SELECT subject_id, MAX(review_id) AS review_id
                FROM candidate_reviews
                WHERE subject_kind = 'visual'
                GROUP BY subject_id
            )
            SELECT v.visual_id, v.portrait_id, v.revision_id,
                   v.motion_recipe_id, v.experiment_id, v.parent_visual_id,
                   v.duration_sec, v.seed,
                   v.generator_version, v.media_path, v.manifest_path,
                   v.status AS render_status,
                   p.intake_filename, p.original_base_filename,
                   pr.file_path AS revision_file_path,
                   p.portrait_group,
                   sp.code AS source_project_code,
                   sp.display_name AS source_project_display_name,
                   cr.review_id, cr.rating, cr.rejected, cr.selected, cr.notes
            FROM visual_candidates v
            JOIN portraits p USING(portrait_id)
            JOIN portrait_revisions pr ON pr.revision_id = v.revision_id
            JOIN source_projects sp USING(source_project_id)
            LEFT JOIN latest_review lr ON lr.subject_id = v.visual_id
            LEFT JOIN candidate_reviews cr ON cr.review_id = lr.review_id
            ORDER BY p.created_at, p.portrait_id, v.motion_recipe_id, v.visual_id
            """
        ).fetchall()
    candidates = []
    for row in rows:
        candidate = dict(row)
        candidate["revision_filename"] = Path(candidate["revision_file_path"]).name
        candidate["rejected"] = bool(candidate["rejected"] or 0)
        candidate["selected"] = bool(candidate["selected"] or 0)
        candidate["notes"] = candidate["notes"] or ""
        if candidate["selected"]:
            candidate["review_status"] = "selected"
        elif candidate["rejected"]:
            candidate["review_status"] = "rejected"
        elif candidate["rating"] is not None or candidate["notes"]:
            candidate["review_status"] = "reviewed"
        else:
            candidate["review_status"] = "unreviewed"
        candidate["episode_number"] = None
        candidates.append(candidate)
    return candidates


def list_audio_candidates_for_review(db_path: Path) -> list[dict[str, Any]]:
    """Return standalone audio candidates with their latest review state."""
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            WITH latest_review AS (
                SELECT subject_id, MAX(review_id) AS review_id
                FROM candidate_reviews
                WHERE subject_kind = 'audio'
                GROUP BY subject_id
            )
            SELECT a.audio_id, a.recipe_id, a.duration_sec, a.seed,
                   a.generator_version, a.media_path, a.manifest_path,
                   a.status AS render_status, a.created_at,
                   cr.review_id, cr.rating, cr.rejected, cr.selected, cr.notes
            FROM audio_candidates a
            LEFT JOIN latest_review lr ON lr.subject_id = a.audio_id
            LEFT JOIN candidate_reviews cr ON cr.review_id = lr.review_id
            ORDER BY a.created_at, a.audio_id
            """
        ).fetchall()
    candidates = []
    for row in rows:
        candidate = dict(row)
        candidate["rejected"] = bool(candidate["rejected"] or 0)
        candidate["selected"] = bool(candidate["selected"] or 0)
        candidate["notes"] = candidate["notes"] or ""
        if candidate["selected"]:
            candidate["review_status"] = "approved for bank"
        elif candidate["rejected"]:
            candidate["review_status"] = "rejected"
        elif candidate["rating"] is not None or candidate["notes"]:
            candidate["review_status"] = "reviewed"
        else:
            candidate["review_status"] = "unreviewed"
        candidates.append(candidate)
    return candidates


def register_audio_candidate(
    db_path: Path,
    *,
    audio_id: str,
    recipe_id: str,
    duration_sec: float,
    seed: int,
    generator_version: str,
    media_path: Path,
    manifest_path: Path,
    status: str = "banked",
) -> None:
    """Register reusable audio idempotently without changing its provenance."""
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    initialize_registry(db_path)
    values = {
        "recipe_id": recipe_id,
        "duration_sec": float(duration_sec),
        "seed": seed,
        "generator_version": generator_version,
    }
    with _connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT recipe_id, duration_sec, seed, generator_version
            FROM audio_candidates WHERE audio_id=?
            """,
            (audio_id,),
        ).fetchone()
        if existing:
            changed = [
                field for field, value in values.items() if existing[field] != value
            ]
            if changed:
                raise ValueError(
                    f"Audio candidate {audio_id} already has different provenance: "
                    + ", ".join(changed)
                )
            connection.execute(
                """
                UPDATE audio_candidates
                SET media_path=?, manifest_path=?,
                    status=CASE
                        WHEN status IN (
                            'retired', 'retired_selected', 'superseded_setup'
                        ) THEN status
                        ELSE ?
                    END
                WHERE audio_id=?
                """,
                (
                    str(media_path.resolve()),
                    str(manifest_path.resolve()),
                    status,
                    audio_id,
                ),
            )
            return
        connection.execute(
            """
            INSERT INTO audio_candidates(
                audio_id, recipe_id, duration_sec, seed, generator_version,
                media_path, manifest_path, status, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_id,
                recipe_id,
                duration_sec,
                seed,
                generator_version,
                str(media_path.resolve()),
                str(manifest_path.resolve()),
                status,
                _now(),
            ),
        )


def register_pair_candidate(
    db_path: Path,
    *,
    pair_id: str,
    experiment_id: str = "unspecified",
    portrait_id: str,
    visual_id: str,
    audio_id: str,
    media_path: Path,
    manifest_path: Path,
    status: str = "ready_for_review",
) -> None:
    """Register a visual/audio pairing idempotently."""
    initialize_registry(db_path)
    values = {
        "experiment_id": experiment_id,
        "portrait_id": portrait_id,
        "visual_id": visual_id,
        "audio_id": audio_id,
    }
    with _connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT experiment_id, portrait_id, visual_id, audio_id
            FROM pair_candidates WHERE pair_id=?
            """,
            (pair_id,),
        ).fetchone()
        if existing:
            changed = [
                field for field, value in values.items() if existing[field] != value
            ]
            if changed:
                raise ValueError(
                    f"Pair candidate {pair_id} already has different provenance: "
                    + ", ".join(changed)
                )
            connection.execute(
                """
                UPDATE pair_candidates
                SET media_path=?, manifest_path=?,
                    status=CASE
                        WHEN status IN (
                            'reviewed', 'rejected_pair', 'selected', 'superseded',
                            'superseded_setup'
                        ) THEN status
                        ELSE ?
                    END
                WHERE pair_id=?
                """,
                (
                    str(media_path.resolve()),
                    str(manifest_path.resolve()),
                    status,
                    pair_id,
                ),
            )
            return
        visual = connection.execute(
            "SELECT portrait_id FROM visual_candidates WHERE visual_id=?",
            (visual_id,),
        ).fetchone()
        if not visual:
            raise ValueError(f"Unknown visual candidate: {visual_id}")
        if visual["portrait_id"] != portrait_id:
            raise ValueError(f"Visual {visual_id} does not belong to {portrait_id}")
        if not connection.execute(
            "SELECT 1 FROM audio_candidates WHERE audio_id=?", (audio_id,)
        ).fetchone():
            raise ValueError(f"Unknown audio candidate: {audio_id}")
        connection.execute(
            """
            INSERT INTO pair_candidates(
                pair_id, experiment_id, portrait_id, visual_id, audio_id, media_path,
                manifest_path, status, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pair_id,
                experiment_id,
                portrait_id,
                visual_id,
                audio_id,
                str(media_path.resolve()),
                str(manifest_path.resolve()),
                status,
                _now(),
            ),
        )


def supersede_pair_experiment(db_path: Path, experiment_id: str) -> int:
    """Retain a setup-error pair round for audit while removing it from active use."""
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        pairs = connection.execute(
            """
            SELECT pair_id, audio_id, status
            FROM pair_candidates
            WHERE experiment_id=?
            """,
            (experiment_id,),
        ).fetchall()
        if any(pair["status"] == "selected" for pair in pairs):
            raise ValueError(f"Cannot supersede selected experiment: {experiment_id}")
        if not pairs:
            return 0
        connection.execute(
            """
            UPDATE pair_candidates
            SET status='superseded_setup'
            WHERE experiment_id=?
            """,
            (experiment_id,),
        )
        for pair in pairs:
            used_elsewhere = connection.execute(
                """
                SELECT 1
                FROM pair_candidates
                WHERE audio_id=? AND experiment_id<>?
                  AND status NOT IN ('superseded', 'superseded_setup')
                LIMIT 1
                """,
                (pair["audio_id"], experiment_id),
            ).fetchone()
            if not used_elsewhere:
                connection.execute(
                    """
                    UPDATE audio_candidates
                    SET status='superseded_setup'
                    WHERE audio_id=? AND status='banked'
                    """,
                    (pair["audio_id"],),
                )
        return len(pairs)


def list_pair_candidates_for_review(db_path: Path) -> list[dict[str, Any]]:
    """Return visual/audio pairs and their separate latest review states."""
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            WITH latest_pair_review AS (
                SELECT subject_id, MAX(review_id) AS review_id
                FROM candidate_reviews
                WHERE subject_kind='pair'
                GROUP BY subject_id
            ), latest_audio_review AS (
                SELECT subject_id, MAX(review_id) AS review_id
                FROM candidate_reviews
                WHERE subject_kind='audio'
                GROUP BY subject_id
            )
            SELECT pc.pair_id, pc.experiment_id, pc.portrait_id,
                   pc.visual_id, pc.audio_id,
                   pc.media_path, pc.manifest_path,
                   pc.status AS render_status,
                   v.revision_id, v.motion_recipe_id,
                   a.recipe_id AS audio_recipe_id,
                   a.duration_sec, a.seed AS audio_seed,
                   a.generator_version AS audio_generator_version,
                   a.media_path AS audio_media_path,
                   a.manifest_path AS audio_manifest_path,
                   a.status AS audio_status,
                   p.intake_filename, p.original_base_filename,
                   p.portrait_group,
                   pr.file_path AS revision_file_path,
                   sp.code AS source_project_code,
                   sp.display_name AS source_project_display_name,
                   pcr.review_id AS pair_review_id,
                   pcr.rating AS pair_rating,
                   pcr.rejected AS pair_rejected,
                   pcr.selected AS pair_selected,
                   pcr.notes AS pair_notes,
                   acr.review_id AS audio_review_id,
                   acr.rating AS audio_rating,
                   acr.rejected AS audio_rejected,
                   acr.selected AS audio_selected,
                   acr.notes AS audio_notes
            FROM pair_candidates pc
            JOIN visual_candidates v USING(visual_id)
            JOIN audio_candidates a USING(audio_id)
            JOIN portraits p USING(portrait_id)
            JOIN portrait_revisions pr ON pr.revision_id=v.revision_id
            JOIN source_projects sp USING(source_project_id)
            LEFT JOIN latest_pair_review lpr ON lpr.subject_id=pc.pair_id
            LEFT JOIN candidate_reviews pcr ON pcr.review_id=lpr.review_id
            LEFT JOIN latest_audio_review lar ON lar.subject_id=pc.audio_id
            LEFT JOIN candidate_reviews acr ON acr.review_id=lar.review_id
            ORDER BY pc.created_at, pc.pair_id
            """
        ).fetchall()
    candidates = []
    for row in rows:
        candidate = dict(row)
        candidate["revision_filename"] = Path(candidate["revision_file_path"]).name
        for name in ("pair_rejected", "pair_selected", "audio_rejected", "audio_selected"):
            candidate[name] = bool(candidate[name] or 0)
        candidate["pair_notes"] = candidate["pair_notes"] or ""
        candidate["audio_notes"] = candidate["audio_notes"] or ""
        if candidate["pair_selected"]:
            candidate["review_status"] = "selected"
        elif candidate["pair_rejected"]:
            candidate["review_status"] = "rejected pair"
        elif candidate["pair_rating"] is not None or candidate["pair_notes"]:
            candidate["review_status"] = "reviewed"
        else:
            candidate["review_status"] = "unreviewed"
        candidate["episode_number"] = None
        candidates.append(candidate)
    return candidates


def save_pair_review(
    db_path: Path,
    *,
    pair_id: str,
    pair_rating: int | None,
    audio_rating: int | None,
    rejected: bool,
    selected: bool,
    retire_audio: bool,
    notes: str,
) -> int:
    """Save a pair decision while keeping unused audio available by default."""
    for name, rating in (("pair_rating", pair_rating), ("audio_rating", audio_rating)):
        if rating is not None and rating not in range(1, 6):
            raise ValueError(f"{name} must be between 1 and 5")
    if rejected and selected:
        raise ValueError("A pair cannot be both rejected and selected")
    if selected and retire_audio:
        raise ValueError("Selected audio cannot also be retired")
    if not isinstance(notes, str):
        raise ValueError("notes must be text")
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        pair = connection.execute(
            "SELECT pair_id, portrait_id, audio_id FROM pair_candidates WHERE pair_id=?",
            (pair_id,),
        ).fetchone()
        if not pair:
            raise ValueError(f"Unknown pair candidate: {pair_id}")
        now = _now()
        if selected:
            previous = connection.execute(
                """
                WITH latest_review AS (
                    SELECT subject_id, MAX(review_id) AS review_id
                    FROM candidate_reviews
                    WHERE subject_kind='pair'
                    GROUP BY subject_id
                )
                SELECT pc.pair_id, pc.audio_id, cr.rating, cr.notes
                FROM pair_candidates pc
                JOIN latest_review lr ON lr.subject_id=pc.pair_id
                JOIN candidate_reviews cr ON cr.review_id=lr.review_id
                WHERE pc.portrait_id=? AND pc.pair_id<>? AND cr.selected=1
                """,
                (pair["portrait_id"], pair_id),
            ).fetchall()
            for old in previous:
                connection.execute(
                    """
                    INSERT INTO candidate_reviews(
                        subject_kind, subject_id, rating, rejected, selected,
                        notes, created_at
                    ) VALUES('pair', ?, ?, 0, 0, ?, ?)
                    """,
                    (old["pair_id"], old["rating"], old["notes"], now),
                )
                connection.execute(
                    "UPDATE pair_candidates SET status='superseded' WHERE pair_id=?",
                    (old["pair_id"],),
                )
                connection.execute(
                    "UPDATE audio_candidates SET status='banked' WHERE audio_id=?",
                    (old["audio_id"],),
                )
                old_audio = connection.execute(
                    """
                    SELECT rating, notes FROM candidate_reviews
                    WHERE subject_kind='audio' AND subject_id=?
                    ORDER BY review_id DESC LIMIT 1
                    """,
                    (old["audio_id"],),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO candidate_reviews(
                        subject_kind, subject_id, rating, rejected, selected,
                        notes, created_at
                    ) VALUES('audio', ?, ?, 0, 0, ?, ?)
                    """,
                    (
                        old["audio_id"],
                        old_audio["rating"] if old_audio else None,
                        old_audio["notes"] if old_audio else "",
                        now,
                    ),
                )
        cursor = connection.execute(
            """
            INSERT INTO candidate_reviews(
                subject_kind, subject_id, rating, rejected, selected, notes,
                created_at
            ) VALUES('pair', ?, ?, ?, ?, ?, ?)
            """,
            (pair_id, pair_rating, int(rejected), int(selected), notes, now),
        )
        existing_audio = connection.execute(
            """
            SELECT notes FROM candidate_reviews
            WHERE subject_kind='audio' AND subject_id=?
            ORDER BY review_id DESC LIMIT 1
            """,
            (pair["audio_id"],),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO candidate_reviews(
                subject_kind, subject_id, rating, rejected, selected, notes,
                created_at
            ) VALUES('audio', ?, ?, ?, ?, ?, ?)
            """,
            (
                pair["audio_id"],
                audio_rating,
                int(retire_audio),
                int(selected),
                existing_audio["notes"] if existing_audio else "",
                now,
            ),
        )
        pair_status = "selected" if selected else "rejected_pair" if rejected else "reviewed"
        audio_status = "retired_selected" if selected else "retired" if retire_audio else "banked"
        connection.execute(
            "UPDATE pair_candidates SET status=? WHERE pair_id=?",
            (pair_status, pair_id),
        )
        connection.execute(
            "UPDATE audio_candidates SET status=? WHERE audio_id=?",
            (audio_status, pair["audio_id"]),
        )
        return int(cursor.lastrowid)


def save_candidate_review(
    db_path: Path,
    *,
    subject_kind: str,
    subject_id: str,
    rating: int | None,
    rejected: bool,
    selected: bool,
    notes: str,
) -> int:
    """Append a human review decision and return its audit-log ID."""
    if subject_kind not in {"visual", "audio", "pair"}:
        raise ValueError("subject_kind must be visual, audio, or pair")
    if rating is not None and rating not in range(1, 6):
        raise ValueError("rating must be between 1 and 5")
    if rejected and selected:
        raise ValueError("A candidate cannot be both rejected and selected")
    if not isinstance(notes, str):
        raise ValueError("notes must be text")
    initialize_registry(db_path)
    table_by_kind = {
        "visual": ("visual_candidates", "visual_id"),
        "audio": ("audio_candidates", "audio_id"),
        "pair": ("pair_candidates", "pair_id"),
    }
    table, id_column = table_by_kind[subject_kind]
    with _connect(db_path) as connection:
        subject = connection.execute(
            f"SELECT * FROM {table} WHERE {id_column}=?", (subject_id,)
        ).fetchone()
        if not subject:
            raise ValueError(f"Unknown {subject_kind} candidate: {subject_id}")
        now = _now()
        if subject_kind == "visual" and selected:
            previously_selected = connection.execute(
                """
                WITH latest_review AS (
                    SELECT subject_id, MAX(review_id) AS review_id
                    FROM candidate_reviews
                    WHERE subject_kind='visual'
                    GROUP BY subject_id
                )
                SELECT v.visual_id, cr.rating, cr.notes
                FROM visual_candidates v
                JOIN latest_review lr ON lr.subject_id=v.visual_id
                JOIN candidate_reviews cr ON cr.review_id=lr.review_id
                WHERE v.portrait_id=? AND v.visual_id<>? AND cr.selected=1
                """,
                (subject["portrait_id"], subject_id),
            ).fetchall()
            connection.executemany(
                """
                INSERT INTO candidate_reviews(
                    subject_kind, subject_id, rating, rejected, selected,
                    notes, created_at
                ) VALUES('visual', ?, ?, 0, 0, ?, ?)
                """,
                [
                    (row["visual_id"], row["rating"], row["notes"], now)
                    for row in previously_selected
                ],
            )
        cursor = connection.execute(
            """
            INSERT INTO candidate_reviews(
                subject_kind, subject_id, rating, rejected, selected, notes,
                created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject_kind,
                subject_id,
                rating,
                int(rejected),
                int(selected),
                notes,
                now,
            ),
        )
        if subject_kind == "audio":
            audio_status = (
                "retired" if rejected else "banked" if selected else "ready_for_review"
            )
            connection.execute(
                "UPDATE audio_candidates SET status=? WHERE audio_id=?",
                (audio_status, subject_id),
            )
        return int(cursor.lastrowid)


def register_final_master(
    db_path: Path,
    *,
    master_id: str,
    portrait_id: str,
    revision_id: str,
    media_path: Path,
    manifest_path: Path,
    status: str = "approved",
) -> None:
    initialize_registry(db_path)
    now = _now()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO final_masters(
                master_id, portrait_id, revision_id, media_path, manifest_path,
                status, approved_at, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                master_id,
                portrait_id,
                revision_id,
                str(media_path),
                str(manifest_path),
                status,
                now if status == "approved" else None,
                now,
            ),
        )


def create_sequence(db_path: Path, name: str, expected_count: int = 120) -> str:
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        version = connection.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM sequence_versions"
        ).fetchone()[0]
        sequence_id = f"SEQ-{version:04d}"
        connection.execute(
            """
            INSERT INTO sequence_versions(
                sequence_id, version_number, name, expected_count, created_at
            ) VALUES(?, ?, ?, ?, ?)
            """,
            (sequence_id, version, name, expected_count, _now()),
        )
    return sequence_id


def set_sequence_order(
    db_path: Path, sequence_id: str, ordered_master_ids: Sequence[str]
) -> None:
    if len(set(ordered_master_ids)) != len(ordered_master_ids):
        raise ValueError("A sequence cannot contain a master more than once")
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        sequence = connection.execute(
            "SELECT status FROM sequence_versions WHERE sequence_id=?",
            (sequence_id,),
        ).fetchone()
        if not sequence:
            raise ValueError(f"Unknown sequence: {sequence_id}")
        if sequence["status"] != "draft":
            raise ValueError("Only a draft sequence can be reordered")

        masters: dict[str, sqlite3.Row] = {}
        if ordered_master_ids:
            placeholders = ",".join("?" for _ in ordered_master_ids)
            rows = connection.execute(
                f"""
                SELECT master_id, portrait_id, status FROM final_masters
                WHERE master_id IN ({placeholders})
                """,
                tuple(ordered_master_ids),
            ).fetchall()
            masters = {row["master_id"]: row for row in rows}
        missing = [master for master in ordered_master_ids if master not in masters]
        if missing:
            raise ValueError(f"Unknown final masters: {', '.join(missing)}")
        unapproved = [
            master for master in ordered_master_ids
            if masters[master]["status"] != "approved"
        ]
        if unapproved:
            raise ValueError(f"Unapproved final masters: {', '.join(unapproved)}")

        connection.execute(
            "DELETE FROM sequence_entries WHERE sequence_id=?", (sequence_id,)
        )
        connection.executemany(
            """
            INSERT INTO sequence_entries(sequence_id, position, master_id, portrait_id)
            VALUES(?, ?, ?, ?)
            """,
            [
                (sequence_id, position, master_id, masters[master_id]["portrait_id"])
                for position, master_id in enumerate(ordered_master_ids, start=1)
            ],
        )


def lock_sequence(db_path: Path, sequence_id: str) -> None:
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        sequence = connection.execute(
            """
            SELECT status, expected_count FROM sequence_versions WHERE sequence_id=?
            """,
            (sequence_id,),
        ).fetchone()
        if not sequence:
            raise ValueError(f"Unknown sequence: {sequence_id}")
        if sequence["status"] != "draft":
            raise ValueError("Only a draft sequence can be locked")
        entries = connection.execute(
            """
            SELECT position, master_id FROM sequence_entries
            WHERE sequence_id=? ORDER BY position
            """,
            (sequence_id,),
        ).fetchall()
        if len(entries) != sequence["expected_count"]:
            raise ValueError(
                f"Sequence requires {sequence['expected_count']} masters; found {len(entries)}"
            )
        locked_at = _now()
        connection.execute(
            "UPDATE sequence_versions SET status='locked', locked_at=? WHERE sequence_id=?",
            (locked_at, sequence_id),
        )
        connection.executemany(
            """
            INSERT INTO publication_records(
                publication_id, sequence_id, episode_number, master_id, status
            ) VALUES(?, ?, ?, ?, 'not_scheduled')
            """,
            [
                (
                    f"PUB-{sequence_id}-{entry['position']:03d}",
                    sequence_id,
                    entry["position"],
                    entry["master_id"],
                )
                for entry in entries
            ],
        )


def get_sequence(db_path: Path, sequence_id: str) -> dict[str, Any]:
    if not db_path.is_file():
        initialize_registry(db_path)
    with _connect(db_path) as connection:
        sequence = connection.execute(
            "SELECT * FROM sequence_versions WHERE sequence_id=?", (sequence_id,)
        ).fetchone()
        if not sequence:
            raise ValueError(f"Unknown sequence: {sequence_id}")
        entries = connection.execute(
            """
            SELECT position, master_id, portrait_id FROM sequence_entries
            WHERE sequence_id=? ORDER BY position
            """,
            (sequence_id,),
        ).fetchall()
    return {**dict(sequence), "entries": [dict(row) for row in entries]}
