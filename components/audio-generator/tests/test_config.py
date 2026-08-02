import unittest

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


if __name__ == "__main__":
    unittest.main()
