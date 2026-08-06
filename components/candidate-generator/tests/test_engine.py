from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hpr_candidate_generator.engine import (
    ArchiveProductionSpec,
    AudioCandidateRecord,
    PairCandidateRecord,
    PortraitInput,
    build_archive_plan,
    plan_pair_options,
    record_pair_review,
    replace_episode_photo,
    write_archive_plan,
)


class ArchiveCandidateEngineTests(unittest.TestCase):
    def portraits(self, count: int = 120) -> list[PortraitInput]:
        return [PortraitInput(f"POR-{i:03d}", Path(f"portraits/{i:03d}.tif")) for i in range(1, count + 1)]

    def test_production_plan_has_balanced_archive_counts(self) -> None:
        plan = build_archive_plan(self.portraits(), seed=2026080601)
        self.assertEqual(120, len(plan.episodes))
        self.assertEqual(600, len(plan.visuals))
        self.assertEqual(150, len(plan.audio))
        self.assertEqual(120, len(plan.publishing))
        self.assertEqual({7: 40, 9: 40, 11: 40}, {
            duration: sum(episode.duration_sec == duration for episode in plan.episodes)
            for duration in (7, 9, 11)
        })
        self.assertTrue(all(episode.mode == "archive" for episode in plan.episodes))

    def test_plan_is_deterministic(self) -> None:
        first = build_archive_plan(self.portraits(), seed=44)
        second = build_archive_plan(self.portraits(), seed=44)
        self.assertEqual(first, second)

    def test_plan_rejects_wrong_portrait_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 120 portraits"):
            build_archive_plan(self.portraits(119), seed=1)

    def test_photo_swap_preserves_creative_assembly(self) -> None:
        original = build_archive_plan(self.portraits(), seed=1).episodes[0]
        assembled = replace(
            original,
            selected_visual_id="VIS-ARC-001-03",
            selected_visual_recipe="VP-024",
            selected_audio_id="AUD-007-014",
            selected_pair_id="PAIR-ARC-001-02",
            text_treatment_id="TXT-LOWER-THIRD-01",
            publication_metadata={"channel": "instagram"},
        )
        swapped = replace_episode_photo(assembled, "POR-001-R2", Path("corrected/001.tif"))
        self.assertEqual(2, swapped.photo_revision)
        self.assertTrue(swapped.renders_stale)
        self.assertEqual(assembled.selected_visual_recipe, swapped.selected_visual_recipe)
        self.assertEqual(assembled.selected_audio_id, swapped.selected_audio_id)
        self.assertEqual(assembled.text_treatment_id, swapped.text_treatment_id)
        self.assertEqual(assembled.publication_metadata, swapped.publication_metadata)

    def test_pair_options_are_duration_compatible_and_skip_retired_audio(self) -> None:
        plan = build_archive_plan(self.portraits(), seed=2)
        episode = replace(plan.episodes[0], selected_visual_id=plan.visuals[0].visual_id)
        bank = tuple(
            replace(audio, status="retired") if audio.audio_id == "AUD-007-001" else audio
            for audio in plan.audio
        )
        pairs = plan_pair_options(episode, bank, count=10, seed=2)
        self.assertEqual(10, len(pairs))
        self.assertTrue(all(pair.duration_sec == 7 for pair in pairs))
        self.assertNotIn("AUD-007-001", {pair.audio_id for pair in pairs})
        self.assertEqual(10, len({pair.audio_id for pair in pairs}))

    def test_pair_review_keeps_component_and_pair_judgments_separate(self) -> None:
        pair = PairCandidateRecord("PAIR-1", "ARC-001", "VIS-1", "AUD-1", 7)
        reviewed = record_pair_review(
            pair,
            visual_rating=5,
            audio_rating=5,
            pair_rating=2,
            status="reject_pair_bank_components",
            note="Excellent pieces, wrong relationship",
        )
        self.assertEqual((5, 5, 2), (reviewed.visual_rating, reviewed.audio_rating, reviewed.pair_rating))

    def test_plan_writes_separate_banks_and_summary(self) -> None:
        with TemporaryDirectory() as directory:
            plan = build_archive_plan(self.portraits(), seed=3)
            paths = write_archive_plan(plan, Path(directory))
            summary = json.loads(paths["summary"].read_text())
            self.assertEqual("deferred", summary["now_mode"])
            self.assertEqual(600, summary["counts"]["visual_candidates"])
            self.assertEqual(150, summary["counts"]["audio_candidates"])
            self.assertEqual("", paths["pair"].read_text())


if __name__ == "__main__":
    unittest.main()
