from pathlib import Path
from tempfile import TemporaryDirectory
import io
import json
import unittest
from unittest.mock import patch

from PIL import Image

from hpr_video_generator.config import load_config
from hpr_video_generator.development import (
    DevelopmentCandidate,
    build_development_filter,
    development_mask_frames,
    estimate_focal_point,
    generate_development_candidate,
    load_development_config,
    prepare_source_pair,
)
from hpr_video_generator.infinity_background import (
    background_effect_frame,
    build_background_context,
    build_infinity_background_filter,
    load_infinity_background_config,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeProcess:
    latest_command = None

    def __init__(self, *args, **kwargs) -> None:
        type(self).latest_command = args[0]
        self.stdin = io.BytesIO()
        self.killed = False

    def wait(self) -> int:
        return 0

    def kill(self) -> None:
        self.killed = True


class DevelopmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.video_config = load_config(ROOT / "config/generator.xml")
        self.development_config = load_development_config(
            ROOT / "config/portrait-development-recipes.json"
        )
        self.round2_config = load_development_config(
            ROOT / "config/portrait-development-round2-recipes.json"
        )
        self.finalist_config = load_development_config(
            ROOT / "config/portrait-development-finalist-recipes.json"
        )
        self.visibility_config = load_development_config(
            ROOT / "config/portrait-development-visibility-recipes.json"
        )
        self.settlement_config = load_development_config(
            ROOT / "config/portrait-development-settlement-recipes.json"
        )
        self.infinity_background_config = load_infinity_background_config(
            ROOT / "config/infinity-background-recipes.json"
        )

    def test_pilot_has_five_fixed_geometry_recipes(self) -> None:
        self.assertEqual("portrait-development-pilot-v5", self.development_config.experiment_id)
        self.assertEqual(
            ["PDA-001", "PDA-002", "PDA-003", "PDA-004", "PDA-005"],
            list(self.development_config.recipes),
        )
        self.assertEqual(
            {"static_reference", "global_development", "activation_field", "soft_sweep"},
            {recipe.mode for recipe in self.development_config.recipes.values()},
        )

    def test_every_mask_is_one_direction_and_closes_exactly(self) -> None:
        width = int(self.development_config.mask["width"])
        height = int(self.development_config.mask["height"])
        for recipe in self.development_config.recipes.values():
            masks, timeline = development_mask_frames(
                recipe,
                seed=123,
                frames=168,
                width=width,
                height=height,
                focal_point=(0.5, 0.45),
                mask_settings=self.development_config.mask,
            )
            self.assertEqual(168, len(masks))
            self.assertEqual(masks[0], masks[-1])
            self.assertTrue(
                all(
                    recipe.base_final_mix <= item["minimumFinalMix"] <= 1
                    and recipe.base_final_mix <= item["maximumFinalMix"] <= 1
                    for item in timeline
                )
            )

    def test_static_reference_is_untouched_finished_source(self) -> None:
        recipe = self.development_config.recipes["PDA-001"]
        masks, timeline = development_mask_frames(
            recipe,
            seed=123,
            frames=12,
            width=27,
            height=48,
            focal_point=(0.5, 0.5),
            mask_settings=self.development_config.mask,
        )
        self.assertTrue(all(set(mask) == {255} for mask in masks))
        self.assertTrue(all(item["meanFinalMix"] == 1 for item in timeline))

    def test_activation_field_has_spatial_range(self) -> None:
        recipe = self.development_config.recipes["PDA-004"]
        _, timeline = development_mask_frames(
            recipe,
            seed=456,
            frames=48,
            width=54,
            height=96,
            focal_point=(0.58, 0.42),
            mask_settings=self.development_config.mask,
        )
        self.assertTrue(
            any(item["maximumFinalMix"] - item["minimumFinalMix"] > 0.12 for item in timeline)
        )

    def test_source_pair_is_aligned_and_under_resolved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            portrait = root / "portrait.jpg"
            Image.new("RGB", (90, 160), (145, 105, 80)).save(portrait)
            final = root / "final.png"
            surrogate = root / "surrogate.png"
            provenance = prepare_source_pair(
                portrait, final, surrogate, self.development_config.surrogate
            )
            with Image.open(final) as final_image, Image.open(surrogate) as under:
                self.assertEqual(final_image.size, under.size)
                self.assertNotEqual(final_image.getpixel((45, 80)), under.getpixel((45, 80)))
            self.assertEqual(90, provenance["sourceWidth"])
            self.assertTrue(provenance["normalizedFinalSha256"])

    def test_filter_has_no_geometric_animation(self) -> None:
        graph = build_development_filter(self.video_config, 135, 240)
        self.assertIn("maskedmerge", graph)
        self.assertIn("fps=24", graph)
        self.assertIn("gbrp16le", graph)
        self.assertIn("gray16le", graph)
        self.assertIn(
            "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709",
            graph,
        )
        self.assertNotIn("zoompan", graph)
        self.assertNotIn("rotate", graph)
        self.assertNotIn("displace", graph)

    @patch("hpr_video_generator.development.subprocess.Popen", FakeProcess)
    def test_manifest_records_fixed_geometry_and_exact_telemetry(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            portrait = root / "portrait.jpg"
            Image.new("RGB", (90, 160), (145, 105, 80)).save(portrait)
            output = root / "candidate.mp4"
            generate_development_candidate(
                self.video_config,
                self.development_config,
                DevelopmentCandidate(
                    "POR-TEST",
                    "POR-TEST-R001",
                    portrait,
                    self.development_config.recipes["PDA-003"],
                    789,
                    7,
                    output,
                ),
                ffmpeg="ffmpeg",
            )
            manifest = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual("visual_portrait_development", manifest["candidateType"])
            self.assertEqual("single finished source, one-direction reveal", manifest["sourceModel"])
            self.assertFalse(manifest["overshootAllowed"])
            self.assertTrue(manifest["geometry"]["fixed"])
            self.assertEqual("none", manifest["geometry"]["displacement"])
            self.assertEqual(168, len(manifest["developmentTelemetry"]["frameTimeline"]))
            self.assertTrue(manifest["field"]["firstLastMaskIdentical"])
            command = FakeProcess.latest_command
            self.assertIsNotNone(command)
            self.assertEqual(3, command.count("-framerate"))
            self.assertTrue(
                all(command[index + 1] == "24" for index, item in enumerate(command) if item == "-framerate")
            )

    def test_focal_estimate_is_normalized(self) -> None:
        with TemporaryDirectory() as directory:
            portrait = Path(directory) / "portrait.jpg"
            image = Image.new("RGB", (90, 160), "black")
            for x in range(55, 80):
                for y in range(45, 110):
                    image.putpixel((x, y), (220, 170, 130))
            image.save(portrait)
            x, y = estimate_focal_point(portrait, 54, 96)
            self.assertTrue(0 <= x <= 1)
            self.assertTrue(0 <= y <= 1)

    def test_round_two_has_five_new_traceable_recipes(self) -> None:
        self.assertEqual(
            "portrait-development-tiff-v6", self.round2_config.experiment_id
        )
        self.assertEqual(
            ["PDB-001", "PDB-002", "PDB-003", "PDB-004", "PDB-005"],
            list(self.round2_config.recipes),
        )
        self.assertEqual(
            0.67, self.round2_config.recipes["PDB-002"].base_final_mix
        )
        self.assertEqual(
            0.70, self.round2_config.recipes["PDB-005"].base_final_mix
        )
        self.assertNotEqual(
            self.round2_config.recipes["PDB-003"].speed,
            self.round2_config.recipes["PDB-004"].speed,
        )

    def test_round_two_uses_full_final_rests_and_exact_loop(self) -> None:
        width = int(self.round2_config.mask["width"])
        height = int(self.round2_config.mask["height"])
        for recipe in self.round2_config.recipes.values():
            masks, timeline = development_mask_frames(
                recipe,
                seed=123,
                frames=264,
                width=width,
                height=height,
                focal_point=(0.5, 0.45),
                mask_settings=self.round2_config.mask,
            )
            self.assertEqual(masks[0], masks[-1])
            self.assertEqual({255}, set(masks[0]))
            self.assertTrue(
                all(
                    recipe.base_final_mix <= item["minimumFinalMix"] <= 1
                    and recipe.base_final_mix <= item["maximumFinalMix"] <= 1
                    for item in timeline
                )
            )
        global_timeline = development_mask_frames(
            self.round2_config.recipes["PDB-002"],
            seed=123,
            frames=264,
            width=width,
            height=height,
            focal_point=(0.5, 0.45),
            mask_settings=self.round2_config.mask,
        )[1]
        fully_finished = sum(item["minimumFinalMix"] == 1 for item in global_timeline)
        self.assertGreaterEqual(fully_finished, 130)

    def test_finalist_round_is_narrowed_from_review_notes(self) -> None:
        self.assertEqual(
            "portrait-development-finalist-v7", self.finalist_config.experiment_id
        )
        self.assertEqual(
            ["PDC-001", "PDC-002", "PDC-003"],
            list(self.finalist_config.recipes),
        )
        self.assertEqual(
            {"activation_field", "soft_sweep"},
            {recipe.mode for recipe in self.finalist_config.recipes.values()},
        )
        self.assertTrue(
            all(recipe.finished_hold == 0.128 for recipe in self.finalist_config.recipes.values())
        )
        self.assertEqual(0.50, self.finalist_config.recipes["PDC-003"].base_final_mix)

    def test_finalist_round_has_short_full_final_pause_and_exact_loop(self) -> None:
        width = int(self.finalist_config.mask["width"])
        height = int(self.finalist_config.mask["height"])
        for recipe in self.finalist_config.recipes.values():
            masks, timeline = development_mask_frames(
                recipe,
                seed=123,
                frames=264,
                width=width,
                height=height,
                focal_point=(0.5, 0.45),
                mask_settings=self.finalist_config.mask,
            )
            self.assertEqual(masks[0], masks[-1])
            self.assertEqual({255}, set(masks[0]))
            fully_finished = sum(
                item["minimumFinalMix"] == 1 for item in timeline
            )
            self.assertGreaterEqual(fully_finished, 30)
            self.assertLessEqual(fully_finished, 40)
            self.assertTrue(
                all(
                    recipe.base_final_mix <= item["minimumFinalMix"] <= 1
                    and recipe.base_final_mix <= item["maximumFinalMix"] <= 1
                    for item in timeline
                )
            )

    def test_visibility_round_pushes_every_candidate_harder(self) -> None:
        self.assertEqual(
            "portrait-development-visibility-v8", self.visibility_config.experiment_id
        )
        self.assertEqual(
            ["PDD-001", "PDD-002", "PDD-003"],
            list(self.visibility_config.recipes),
        )
        self.assertTrue(
            all(
                recipe.base_final_mix <= 0.25
                for recipe in self.visibility_config.recipes.values()
            )
        )
        self.assertEqual(0.0, self.visibility_config.recipes["PDD-003"].base_final_mix)
        self.assertLess(
            self.visibility_config.recipes["PDD-002"].feather,
            self.finalist_config.recipes["PDC-002"].feather,
        )

    def test_visibility_round_has_brief_pause_and_exact_loop(self) -> None:
        width = int(self.visibility_config.mask["width"])
        height = int(self.visibility_config.mask["height"])
        for recipe in self.visibility_config.recipes.values():
            masks, timeline = development_mask_frames(
                recipe,
                seed=123,
                frames=264,
                width=width,
                height=height,
                focal_point=(0.5, 0.45),
                mask_settings=self.visibility_config.mask,
            )
            self.assertEqual(masks[0], masks[-1])
            self.assertEqual({255}, set(masks[0]))
            fully_finished = sum(
                item["minimumFinalMix"] == 1 for item in timeline
            )
            self.assertGreaterEqual(fully_finished, 8)
            self.assertLessEqual(fully_finished, 20)
            self.assertTrue(
                all(
                    recipe.base_final_mix <= item["minimumFinalMix"] <= 1
                    and recipe.base_final_mix <= item["maximumFinalMix"] <= 1
                    for item in timeline
                )
            )

    def test_settlement_round_is_exactly_65_percent_toward_visibility(self) -> None:
        self.assertEqual(
            "portrait-development-settlement-v9", self.settlement_config.experiment_id
        )
        self.assertEqual(
            ["PDE-001", "PDE-002", "PDE-003"],
            list(self.settlement_config.recipes),
        )
        pairs = [
            ("PDC-001", "PDD-001", "PDE-001"),
            ("PDC-002", "PDD-002", "PDE-002"),
            ("PDC-003", "PDD-003", "PDE-003"),
        ]
        continuous_fields = [
            "base_final_mix",
            "patch_size_min",
            "patch_size_max",
            "feather",
            "neighbor_coupling",
            "speed",
            "finished_hold",
            "ease_power",
        ]
        for finalist_id, visibility_id, settlement_id in pairs:
            finalist = self.finalist_config.recipes[finalist_id]
            visibility = self.visibility_config.recipes[visibility_id]
            settlement = self.settlement_config.recipes[settlement_id]
            for field in continuous_fields:
                expected = getattr(finalist, field) + 0.65 * (
                    getattr(visibility, field) - getattr(finalist, field)
                )
                self.assertAlmostEqual(expected, getattr(settlement, field), places=6)
        self.assertEqual(4, self.settlement_config.recipes["PDE-001"].patch_count)
        self.assertEqual(5, self.settlement_config.recipes["PDE-003"].patch_count)

    def test_settlement_round_has_intermediate_pause_and_exact_loop(self) -> None:
        width = int(self.settlement_config.mask["width"])
        height = int(self.settlement_config.mask["height"])
        for recipe in self.settlement_config.recipes.values():
            masks, timeline = development_mask_frames(
                recipe,
                seed=123,
                frames=264,
                width=width,
                height=height,
                focal_point=(0.5, 0.45),
                mask_settings=self.settlement_config.mask,
            )
            self.assertEqual(masks[0], masks[-1])
            self.assertEqual({255}, set(masks[0]))
            fully_finished = sum(item["minimumFinalMix"] == 1 for item in timeline)
            self.assertGreaterEqual(fully_finished, 18)
            self.assertLessEqual(fully_finished, 28)
            self.assertTrue(
                all(
                    recipe.base_final_mix <= item["minimumFinalMix"] <= 1
                    and recipe.base_final_mix <= item["maximumFinalMix"] <= 1
                    for item in timeline
                )
            )

    def test_infinity_background_config_has_seven_distinct_effects(self) -> None:
        self.assertEqual(
            "infinity-background-v10", self.infinity_background_config.experiment_id
        )
        self.assertEqual(
            [f"INF-{index:03d}" for index in range(1, 8)],
            list(self.infinity_background_config.recipes),
        )
        self.assertEqual(
            7,
            len(
                {
                    recipe.effect
                    for recipe in self.infinity_background_config.recipes.values()
                }
            ),
        )
        self.assertEqual(
            "PDE-002",
            self.infinity_background_config.base_portrait_treatment[
                "developmentRecipeId"
            ],
        )

    def test_infinity_background_effects_are_visible_and_loop_exactly(self) -> None:
        import numpy as np

        height, width = 48, 27
        background = np.full((height, width, 3), 62000, dtype=np.uint16)
        subject = np.zeros((height, width, 3), dtype=np.uint16)
        subject[:, :, 0] = 42000
        subject[:, :, 1] = 30000
        subject[:, :, 2] = 24000
        alpha = np.zeros((height, width), dtype=np.uint16)
        alpha[8:42, 7:22] = 65535
        context = build_background_context(background, subject, alpha)
        for recipe in self.infinity_background_config.recipes.values():
            first = background_effect_frame(recipe, 0.0, context)
            middle = background_effect_frame(recipe, 0.5, context)
            last = background_effect_frame(recipe, 1.0, context)
            self.assertTrue(np.array_equal(first, last), recipe.id)
            self.assertTrue(np.array_equal(first, background), recipe.id)
            self.assertGreater(
                float(np.abs(middle.astype(np.int32) - first.astype(np.int32)).mean()),
                1.0,
                recipe.id,
            )

    def test_infinity_background_filter_preserves_subject_geometry(self) -> None:
        graph = build_infinity_background_filter(self.video_config, 135, 240)
        self.assertEqual(2, graph.count("maskedmerge"))
        self.assertIn("alphaextract", graph)
        self.assertIn("gbrp16le", graph)
        self.assertIn("fps=24", graph)
        self.assertNotIn("zoompan", graph)
        self.assertNotIn("rotate", graph)
        self.assertNotIn("displace", graph)


if __name__ == "__main__":
    unittest.main()
