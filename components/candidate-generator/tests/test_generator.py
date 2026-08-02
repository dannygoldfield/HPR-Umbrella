from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hpr_candidate_generator.generator import build_plan, mux
from hpr_candidate_generator.cli import DEFAULT_AUDIO_RECIPES


class CandidatePlanTests(unittest.TestCase):
    def test_every_supported_duration_has_a_seamless_default_recipe(self) -> None:
        self.assertEqual(
            {7: "AR-008", 9: "AR-009", 11: "AR-010"},
            DEFAULT_AUDIO_RECIPES,
        )

    def test_plan_is_deterministic_and_separates_work_from_review_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_plan(
                Path("portraits/Jane Doe.tif"),
                Path("grain.mov"),
                9,
                42,
                "VP-012",
                "AR-002",
                root,
            )
            second = build_plan(
                Path("portraits/Jane Doe.tif"),
                Path("grain.mov"),
                9,
                42,
                "VP-012",
                "AR-002",
                root,
            )
            self.assertEqual(first, second)
            self.assertEqual(
                "HPR-Jane-Doe-9s-VP-012-AR-002-seed-42",
                first.candidate_id,
            )
            self.assertIn("work", first.silent_video.parts)
            self.assertIn("candidates", first.final_video.parts)

    def test_plan_rejects_unsupported_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported duration"):
            build_plan(
                Path("portrait.tif"),
                Path("grain.mov"),
                8,
                1,
                "VP-002",
                "AR-001",
                Path("output"),
            )

    @patch("hpr_candidate_generator.generator.subprocess.run")
    def test_mux_preserves_video_and_adds_aac_audio(self, run) -> None:
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "out/final.mp4"
            output = mux(Path("silent.mp4"), Path("sound.wav"), output_path, "ffmpeg")
            self.assertEqual(output_path, output)
            command = run.call_args.args[0]
            self.assertIn("copy", command)
            self.assertIn("aac", command)
            self.assertIn("-shortest", command)
            run.assert_called_once_with(command, check=True)


if __name__ == "__main__":
    unittest.main()
