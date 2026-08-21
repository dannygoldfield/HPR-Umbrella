from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from hpr_registry.registry import (
    create_sequence,
    get_sequence,
    ingest_metadata_report,
    initialize_registry,
    list_current_portrait_revisions,
    list_pair_candidates_for_review,
    list_portraits,
    list_visual_candidates_for_review,
    lock_sequence,
    register_audio_candidate,
    register_final_master,
    register_pair_candidate,
    register_visual_candidate,
    save_candidate_review,
    save_pair_review,
    set_sequence_order,
)


def metadata_result(path: Path, pilot: str) -> dict:
    def field(value, tag):
        return {"expected": value, "status": "match", "locations": [{"tag": tag, "value": value}]}

    return {
        "path": str(path),
        "pilot_id": pilot,
        "filename": {
            "valid": True,
            "mode": "intake",
            "intake_key": path.name,
            "episode_number": None,
            "source_filename": path.name,
            "source_basename": path.stem,
            "error": None,
        },
        "image": {"width": 1080, "height": 1920},
        "fields": {
            "source": field("Project", "XMP:photoshop:Source"),
            "title": field(f"Title {pilot}", "XMP:dc:title"),
            "caption": field(f"Caption {pilot}", "XMP:dc:description"),
            "headline": field(f"Headline {pilot}", "XMP:photoshop:Headline"),
            "alt_text": field(f"Alt {pilot}", "XMP:Iptc4xmpCore:AltTextAccessibility"),
            "extended_description": field(
                f"Extended {pilot}", "XMP:Iptc4xmpCore:ExtDescrAccessibility"
            ),
            "keywords": field([f"keyword-{pilot}"], "XMP:dc:subject"),
            "rating": field(1, "XMP:xmp:Rating"),
            "color_label": field("Red", "XMP:xmp:Label"),
            "creator": field("Creator", "XMP:dc:creator"),
            "copyright": field("Copyright", "XMP:dc:rights"),
        },
        "metadata": {"exif": {}, "iptc": {}, "xmp": {}},
    }


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "registry.sqlite3"
        self.manifests = self.root / "manifests"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_inputs(self, count: int = 1) -> tuple[Path, Path, list[Path]]:
        files = []
        results = []
        config = {"files": {}}
        groups = ["age_12_or_younger", "age_100_plus", "number_prop"]
        for index in range(count):
            path = self.root / f"portrait-{index + 1}.jpg"
            path.write_bytes(f"jpeg-{index}".encode())
            files.append(path)
            pilot = chr(ord("A") + index)
            results.append(metadata_result(path, pilot))
            config["files"][path.name] = {
                "source_project_code": f"Project{index + 1}",
                "source_project_display_name": f"Project {index + 1}",
                "portrait_group": groups[index],
            }
        report = self.root / "report.json"
        report.write_text(json.dumps({"results": results}))
        intake = self.root / "intake.json"
        intake.write_text(json.dumps(config))
        return report, intake, files

    def test_initialization_creates_versioned_schema(self) -> None:
        initialize_registry(self.db)
        with sqlite3.connect(self.db) as connection:
            version = connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]
        self.assertEqual(3, version)

    def test_ingest_assigns_portrait_not_episode_and_is_idempotent(self) -> None:
        report, intake, _ = self.write_inputs()
        first = ingest_metadata_report(self.db, report, intake, self.manifests)
        second = ingest_metadata_report(self.db, report, intake, self.manifests)
        self.assertEqual("ingested", first[0]["action"])
        self.assertEqual("unchanged", second[0]["action"])
        portraits = list_portraits(self.db)
        self.assertEqual(1, len(portraits))
        self.assertNotIn("episode_number", portraits[0])
        self.assertEqual("portrait-1.jpg", portraits[0]["intake_filename"])

    def test_changed_export_creates_revision_without_changing_portrait(self) -> None:
        report, intake, files = self.write_inputs()
        first = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        files[0].write_bytes(b"changed-jpeg")
        second = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        self.assertEqual(first["portrait_id"], second["portrait_id"])
        self.assertEqual(1, first["revision_number"])
        self.assertEqual(2, second["revision_number"])

    def test_tiff_with_same_base_name_creates_revision_of_jpeg_portrait(self) -> None:
        report, intake, files = self.write_inputs()
        first = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        tiff = files[0].with_suffix(".tif")
        tiff.write_bytes(b"sixteen-bit-tiff")
        tiff_report = self.root / "tiff-report.json"
        tiff_report.write_text(json.dumps({"results": [metadata_result(tiff, "A")]}))
        tiff_intake = self.root / "tiff-intake.json"
        tiff_intake.write_text(
            json.dumps(
                {
                    "files": {
                        tiff.name: {
                            "source_project_code": "Project1",
                            "source_project_display_name": "Project 1",
                            "portrait_group": "age_12_or_younger",
                        }
                    }
                }
            )
        )
        second = ingest_metadata_report(
            self.db, tiff_report, tiff_intake, self.manifests
        )[0]
        self.assertEqual(first["portrait_id"], second["portrait_id"])
        self.assertEqual(2, second["revision_number"])
        self.assertEqual(1, len(list_portraits(self.db)))

    def test_visual_candidate_registration_preserves_revision_provenance(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        current = list_current_portrait_revisions(self.db)
        self.assertEqual(ingested["revision_id"], current[0]["revision_id"])
        arguments = {
            "visual_id": "VIS-001",
            "portrait_id": ingested["portrait_id"],
            "revision_id": ingested["revision_id"],
            "motion_recipe_id": "MR-001",
            "experiment_id": "motion-rhythm-pilot-v1",
            "duration_sec": 7,
            "seed": 123,
            "generator_version": "0.1.0",
            "media_path": self.root / "VIS-001.mp4",
            "manifest_path": self.root / "VIS-001.json",
        }
        register_visual_candidate(self.db, **arguments)
        register_visual_candidate(self.db, **arguments)
        with sqlite3.connect(self.db) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM visual_candidates WHERE visual_id='VIS-001'"
            ).fetchone()[0]
        self.assertEqual(1, count)
        with self.assertRaisesRegex(ValueError, "different provenance"):
            register_visual_candidate(
                self.db,
                **{**arguments, "motion_recipe_id": "MR-002"},
            )

    def test_variable_candidate_can_reference_selected_baseline(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        common = {
            "portrait_id": ingested["portrait_id"],
            "revision_id": ingested["revision_id"],
            "duration_sec": 7,
            "seed": 123,
            "generator_version": "0.1.0",
            "media_path": self.root / "candidate.mp4",
            "manifest_path": self.root / "candidate.json",
        }
        register_visual_candidate(
            self.db,
            visual_id="VIS-BASE",
            motion_recipe_id="MR-005",
            experiment_id="motion-rhythm-pilot-v1",
            **common,
        )
        register_visual_candidate(
            self.db,
            visual_id="VIS-VARIABLE",
            motion_recipe_id="MV2-MR005-LOW-SCALE",
            experiment_id="motion-variable-pilot-v2",
            parent_visual_id="VIS-BASE",
            **{**common, "seed": 456},
        )
        candidates = list_visual_candidates_for_review(self.db)
        variable = next(
            candidate
            for candidate in candidates
            if candidate["visual_id"] == "VIS-VARIABLE"
        )
        self.assertEqual("motion-variable-pilot-v2", variable["experiment_id"])
        self.assertEqual("VIS-BASE", variable["parent_visual_id"])
        self.assertEqual("portrait-1.jpg", variable["revision_filename"])

    def test_selecting_new_visual_deselects_prior_visual_for_portrait(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        for visual_id, recipe_id in (("VIS-A", "MR-005"), ("VIS-B", "MV2-LOW")):
            register_visual_candidate(
                self.db,
                visual_id=visual_id,
                portrait_id=ingested["portrait_id"],
                revision_id=ingested["revision_id"],
                motion_recipe_id=recipe_id,
                duration_sec=7,
                seed=123,
                generator_version="0.1.0",
                media_path=self.root / f"{visual_id}.mp4",
                manifest_path=self.root / f"{visual_id}.json",
            )
        for visual_id in ("VIS-A", "VIS-B"):
            save_candidate_review(
                self.db,
                subject_kind="visual",
                subject_id=visual_id,
                rating=4,
                rejected=False,
                selected=True,
                notes="",
            )
        candidates = {
            candidate["visual_id"]: candidate
            for candidate in list_visual_candidates_for_review(self.db)
        }
        self.assertFalse(candidates["VIS-A"]["selected"])
        self.assertTrue(candidates["VIS-B"]["selected"])

    def test_latest_visual_review_is_separate_and_auditable(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        register_visual_candidate(
            self.db,
            visual_id="VIS-REVIEW",
            portrait_id=ingested["portrait_id"],
            revision_id=ingested["revision_id"],
            motion_recipe_id="MR-003",
            duration_sec=7,
            seed=123,
            generator_version="0.1.0",
            media_path=self.root / "VIS-REVIEW.mp4",
            manifest_path=self.root / "VIS-REVIEW.json",
        )
        first_id = save_candidate_review(
            self.db,
            subject_kind="visual",
            subject_id="VIS-REVIEW",
            rating=2,
            rejected=True,
            selected=False,
            notes="First pass",
        )
        second_id = save_candidate_review(
            self.db,
            subject_kind="visual",
            subject_id="VIS-REVIEW",
            rating=4,
            rejected=False,
            selected=True,
            notes="Reconsidered",
        )
        candidate = list_visual_candidates_for_review(self.db)[0]
        self.assertGreater(second_id, first_id)
        self.assertEqual(4, candidate["rating"])
        self.assertTrue(candidate["selected"])
        self.assertEqual("selected", candidate["review_status"])
        self.assertIsNone(candidate["episode_number"])
        with sqlite3.connect(self.db) as connection:
            history_count = connection.execute(
                "SELECT COUNT(*) FROM candidate_reviews"
            ).fetchone()[0]
        self.assertEqual(2, history_count)

    def test_pair_review_keeps_unused_audio_banked_and_moves_selection(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        register_visual_candidate(
            self.db,
            visual_id="VIS-PAIR",
            portrait_id=ingested["portrait_id"],
            revision_id=ingested["revision_id"],
            motion_recipe_id="PDE-002",
            duration_sec=11,
            seed=123,
            generator_version="0.1.0",
            media_path=self.root / "visual.mp4",
            manifest_path=self.root / "visual.json",
        )
        for index in (1, 2):
            audio_id = f"AUD-{index}"
            pair_id = f"PAIR-{index}"
            register_audio_candidate(
                self.db,
                audio_id=audio_id,
                recipe_id="AR-010",
                duration_sec=11,
                seed=100 + index,
                generator_version="0.3.0",
                media_path=self.root / f"{audio_id}.wav",
                manifest_path=self.root / f"{audio_id}.json",
            )
            register_pair_candidate(
                self.db,
                pair_id=pair_id,
                portrait_id=ingested["portrait_id"],
                visual_id="VIS-PAIR",
                audio_id=audio_id,
                media_path=self.root / f"{pair_id}.mp4",
                manifest_path=self.root / f"{pair_id}.json",
            )

        save_pair_review(
            self.db,
            pair_id="PAIR-1",
            pair_rating=5,
            audio_rating=4,
            rejected=False,
            selected=True,
            retire_audio=False,
            notes="First choice",
        )
        first = {item["pair_id"]: item for item in list_pair_candidates_for_review(self.db)}
        self.assertTrue(first["PAIR-1"]["pair_selected"])
        self.assertEqual("retired_selected", first["PAIR-1"]["audio_status"])
        self.assertEqual("banked", first["PAIR-2"]["audio_status"])

        save_pair_review(
            self.db,
            pair_id="PAIR-2",
            pair_rating=5,
            audio_rating=5,
            rejected=False,
            selected=True,
            retire_audio=False,
            notes="New choice",
        )
        second = {item["pair_id"]: item for item in list_pair_candidates_for_review(self.db)}
        self.assertFalse(second["PAIR-1"]["pair_selected"])
        self.assertEqual("banked", second["PAIR-1"]["audio_status"])
        self.assertTrue(second["PAIR-2"]["pair_selected"])
        self.assertEqual("retired_selected", second["PAIR-2"]["audio_status"])

        save_pair_review(
            self.db,
            pair_id="PAIR-1",
            pair_rating=2,
            audio_rating=3,
            rejected=True,
            selected=False,
            retire_audio=False,
            notes="Pair fails, audio remains useful",
        )
        final = {item["pair_id"]: item for item in list_pair_candidates_for_review(self.db)}
        self.assertTrue(final["PAIR-1"]["pair_rejected"])
        self.assertEqual("banked", final["PAIR-1"]["audio_status"])

    def test_pair_review_can_explicitly_retire_audio(self) -> None:
        report, intake, _ = self.write_inputs()
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)[0]
        register_visual_candidate(
            self.db,
            visual_id="VIS-PAIR",
            portrait_id=ingested["portrait_id"],
            revision_id=ingested["revision_id"],
            motion_recipe_id="PDE-002",
            duration_sec=11,
            seed=123,
            generator_version="0.1.0",
            media_path=self.root / "visual.mp4",
            manifest_path=self.root / "visual.json",
        )
        register_audio_candidate(
            self.db,
            audio_id="AUD-RETIRE",
            recipe_id="AR-010",
            duration_sec=11,
            seed=456,
            generator_version="0.3.0",
            media_path=self.root / "audio.wav",
            manifest_path=self.root / "audio.json",
        )
        register_pair_candidate(
            self.db,
            pair_id="PAIR-RETIRE",
            portrait_id=ingested["portrait_id"],
            visual_id="VIS-PAIR",
            audio_id="AUD-RETIRE",
            media_path=self.root / "pair.mp4",
            manifest_path=self.root / "pair.json",
        )
        save_pair_review(
            self.db,
            pair_id="PAIR-RETIRE",
            pair_rating=1,
            audio_rating=1,
            rejected=True,
            selected=False,
            retire_audio=True,
            notes="Audio itself is not reusable",
        )
        candidate = list_pair_candidates_for_review(self.db)[0]
        self.assertEqual("retired", candidate["audio_status"])
        self.assertTrue(candidate["audio_rejected"])

    def test_episode_numbers_appear_only_when_complete_sequence_locks(self) -> None:
        report, intake, _ = self.write_inputs(2)
        ingested = ingest_metadata_report(self.db, report, intake, self.manifests)
        for index, item in enumerate(ingested, start=1):
            register_final_master(
                self.db,
                master_id=f"MASTER-{index}",
                portrait_id=item["portrait_id"],
                revision_id=item["revision_id"],
                media_path=Path(f"master-{index}.mp4"),
                manifest_path=Path(f"master-{index}.json"),
            )
        sequence_id = create_sequence(self.db, "Pilot order", expected_count=2)
        set_sequence_order(self.db, sequence_id, ["MASTER-2", "MASTER-1"])
        self.assertEqual(
            ["MASTER-2", "MASTER-1"],
            [entry["master_id"] for entry in get_sequence(self.db, sequence_id)["entries"]],
        )
        lock_sequence(self.db, sequence_id)
        with sqlite3.connect(self.db) as connection:
            episodes = connection.execute(
                "SELECT episode_number, master_id FROM publication_records ORDER BY episode_number"
            ).fetchall()
        self.assertEqual([(1, "MASTER-2"), (2, "MASTER-1")], episodes)


if __name__ == "__main__":
    unittest.main()
