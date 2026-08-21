import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hpr_audio_generator.config import load_config
from support import AudioFixture


class ConfigTests(unittest.TestCase):
    def test_audio_only_config_is_valid(self) -> None:
        with AudioFixture() as config_path:
            config = load_config(config_path)
            self.assertEqual(90, len(config.assets))
            self.assertGreaterEqual(len(config.profiles), 1)
            self.assertGreaterEqual(len(config.recipes), 1)
            self.assertEqual({"Bed", "Gesture", "Music"}, {asset.role for asset in config.assets})

    def test_asset_root_override_resolves_private_media_library(self) -> None:
        with AudioFixture() as config_path, TemporaryDirectory() as temporary:
            alternate_root = Path(temporary)
            for asset_path in config_path.parent.parent.joinpath("audio/source").rglob("*.wav"):
                destination = alternate_root / asset_path.relative_to(config_path.parent.parent)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(asset_path.read_bytes())
            config = load_config(config_path, asset_root=alternate_root)
            self.assertEqual(alternate_root.resolve(), config.root)
            self.assertTrue(
                all(
                    str(asset.path).startswith(str(alternate_root.resolve()))
                    for asset in config.assets
                )
            )


if __name__ == "__main__":
    unittest.main()
