from pathlib import Path
import tempfile
import unittest

from hpr_video_generator.film_grain import (
    FilmGrainRecipe,
    build_filter,
    load_film_grain_config,
    sample_window,
)


ROOT = Path(__file__).resolve().parents[1]


class FilmGrainConfigTests(unittest.TestCase):
    def test_composite_round_has_three_locked_visuals_and_seven_recipes(self):
        config = load_film_grain_config(
            ROOT / "config/film-grain-composite-recipes.json"
        )
        self.assertEqual("film-grain-composite-v21", config.experiment_id)
        self.assertEqual(3, len(config.base_visuals))
        self.assertEqual(7, len(config.recipes))
        self.assertIsNone(config.recipes[0].plate_id)
        self.assertEqual(0.0, config.recipes[0].opacity)
        self.assertEqual(
            [
                "VIS-30FE48FB73CE-PDE-002",
                "VIS-90500D66EBBF-PDE-002",
                "VIS-4DF5D853ACDA-IBK-001",
            ],
            [item["visualId"] for item in config.base_visuals],
        )
        self.assertEqual(
            {"35mm-light", "super35-light", "16mm-light", "super35-heavy"},
            set(config.plates),
        )

    def test_unknown_plate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(
                """{
                  "version":"1", "experimentId":"x", "purpose":"x",
                  "source":{}, "baseVisuals":[{"visualId":"v"}],
                  "plates":{},
                  "recipes":[{"id":"FGT-001","name":"bad","plate":"missing","opacity":0.1}]
                }""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown plate"):
                load_film_grain_config(path)

    def test_visibility_round_reaches_an_intentional_boundary(self):
        config = load_film_grain_config(
            ROOT / "config/film-grain-visibility-recipes.json"
        )
        self.assertEqual("film-grain-visibility-v22", config.experiment_id)
        self.assertEqual(1, len(config.base_visuals))
        self.assertEqual(7, len(config.recipes))
        boundary = config.recipes[-1]
        self.assertEqual("FGV-007", boundary.id)
        self.assertEqual(1.0, boundary.opacity)
        self.assertEqual(4.0, boundary.signal_gain)
        self.assertEqual(2.5, boundary.texture_scale)


class FilmGrainFilterTests(unittest.TestCase):
    def test_control_uses_same_delivery_transcode_without_grain_input(self):
        recipe = FilmGrainRecipe("FGC-001", "Control", None, 0.0)
        value = build_filter(
            width=1080, height=1920, fps=24, frames=264, recipe=recipe
        )
        self.assertIn("trim=end_frame=264", value)
        self.assertIn("color_primaries=bt709", value)
        self.assertIn("color_trc=bt709", value)
        self.assertIn("colorspace=bt709[out]", value)
        self.assertNotIn("[1:v]", value)

    def test_grain_changes_luma_only_and_passes_chroma_through(self):
        recipe = FilmGrainRecipe(
            "FGV-004", "Visible", "super35-light", 0.65, 1.5, 1.5
        )
        value = build_filter(
            width=1080,
            height=1920,
            fps=24,
            frames=264,
            recipe=recipe,
            start_frame=31,
            crop_fraction=0.25,
        )
        self.assertIn("trim=start_frame=31:end_frame=295", value)
        self.assertIn("format=gray", value)
        self.assertIn("extractplanes=y+u+v", value)
        self.assertIn("crop=720:1280", value)
        self.assertIn("lut=y='clip(128+(val-128)*1.5000,0,255)'", value)
        self.assertIn("all_mode=overlay:all_opacity=0.6500", value)
        self.assertIn("[textured_y][base_u][base_v]mergeplanes", value)

    def test_sample_window_is_repeatable_and_in_bounds(self):
        first = sample_window(123456, source_frames=360, output_frames=264)
        second = sample_window(123456, source_frames=360, output_frames=264)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first[0], 0)
        self.assertLessEqual(first[0], 96)
        self.assertGreaterEqual(first[1], 0.0)
        self.assertLessEqual(first[1], 1.0)


if __name__ == "__main__":
    unittest.main()
